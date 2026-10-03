from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import text
from app.database.connection import get_session
from app.services.accounting_service import AccountingService
from app.services.audit_service import AuditService
from app.services.document_number_service import DocumentNumberService
from app.services.permission_service import PermissionService


class PurchaseReturnService:
    """مرتجع مشتريات مرتبط بالجداول المرجعية الفعلية للمشتريات والمخزون والمحاسبة."""

    @staticmethod
    def money(value):
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def _columns(session, table):
        return {r[1] for r in session.connection().exec_driver_sql(f"PRAGMA table_info({table})").fetchall()}

    @classmethod
    def _ensure_schema(cls, s):
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS purchase_return_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                return_id INTEGER NOT NULL,
                purchase_invoice_item_id INTEGER NULL,
                product_id INTEGER NOT NULL,
                quantity NUMERIC NOT NULL,
                unit_cost NUMERIC NOT NULL DEFAULT 0,
                line_total NUMERIC NOT NULL DEFAULT 0
            )
        """))
        columns = cls._columns(s, "purchase_return_items")
        migrations = {
            "purchase_invoice_item_id": "ALTER TABLE purchase_return_items ADD COLUMN purchase_invoice_item_id INTEGER NULL",
            "unit_cost": "ALTER TABLE purchase_return_items ADD COLUMN unit_cost NUMERIC NOT NULL DEFAULT 0",
            "line_total": "ALTER TABLE purchase_return_items ADD COLUMN line_total NUMERIC NOT NULL DEFAULT 0",
        }
        for column, statement in migrations.items():
            if column not in columns:
                s.execute(text(statement))

    @classmethod
    def create_return(cls, purchase_id, items, reason="إرجاع مشتريات",
                      refund_method="credit", warehouse_id=None, user_id=None):
        if not items:
            raise ValueError("لا توجد أصناف للإرجاع")
        if refund_method not in {"credit","cash","bank","bank_transfer","card"}:
            raise ValueError("طريقة التسوية غير مدعومة")

        with get_session() as s:
            try:
                PermissionService.ensure_schema(s)
                if user_id is None or not PermissionService.has_in_session(s, user_id, "purchase.return.create"):
                    raise PermissionError("لا توجد صلاحية لتنفيذ المرتجع")
                cls._ensure_schema(s)
                invoice=s.execute(text("SELECT * FROM purchase_invoices WHERE id=:id LIMIT 1"),{"id":purchase_id}).mappings().first()
                if not invoice: raise ValueError("فاتورة الشراء غير موجودة")
                if str(invoice.get("status") or "").upper() in {"VOID","CANCELLED"}: raise ValueError("لا يمكن إرجاع فاتورة ملغاة")

                rows=s.execute(text("""
                    SELECT pii.id AS item_id,pii.product_id,pii.quantity,pii.unit_cost,COALESCE(pii.tax_amount,0) AS tax_amount
                    FROM purchase_invoice_items pii
                    WHERE pii.invoice_id=:id ORDER BY pii.id
                """),{"id":purchase_id}).mappings().all()
                originals={int(x["product_id"]):x for x in rows}
                if not originals: raise ValueError("فاتورة الشراء لا تحتوي أصنافًا")

                prepared=[]; subtotal=Decimal("0"); tax=Decimal("0")
                for item in items:
                    pid=int(item["product_id"]); qty=Decimal(str(item["quantity"]))
                    if qty<=0: raise ValueError("كمية الإرجاع يجب أن تكون أكبر من صفر")
                    original=originals.get(pid)
                    if not original: raise ValueError(f"الصنف غير موجود في الفاتورة: {pid}")
                    already=Decimal(str(s.execute(text("""
                        SELECT COALESCE(SUM(pri.quantity),0)
                        FROM purchase_return_items pri
                        JOIN purchase_returns pr ON pr.id=pri.return_id
                        WHERE pr.invoice_id=:invoice AND pri.product_id=:product
                          AND UPPER(COALESCE(pr.status,'')) NOT IN ('VOID','CANCELLED')
                    """),{"invoice":purchase_id,"product":pid}).scalar() or 0))
                    original_qty=Decimal(str(original["quantity"] or 0))
                    if qty+already>original_qty: raise ValueError(f"الكمية المرتجعة أكبر من المسموح للصنف {pid}")
                    cost=Decimal(str(original["unit_cost"] or 0))
                    tax_per=Decimal(str(original["tax_amount"] or 0))/original_qty if original_qty else Decimal("0")
                    line=cls.money(qty*cost); line_tax=cls.money(qty*tax_per)
                    subtotal+=line; tax+=line_tax
                    prepared.append((int(original["item_id"]),pid,qty,cost,line,line_tax))

                subtotal=cls.money(subtotal); tax=cls.money(tax); total=cls.money(subtotal+tax)
                return_number=DocumentNumberService.next_number(s,"PURCHASE_RETURN","PR",6)
                wh=int(warehouse_id or invoice.get("warehouse_id") or 1)

                s.execute(text("""
                    INSERT INTO purchase_returns(return_number,supplier_id,invoice_id,reason,total_amount,status,created_at)
                    VALUES(:number,:supplier,:invoice,:reason,:total,'POSTED',CURRENT_TIMESTAMP)
                """),{"number":return_number,"supplier":invoice["supplier_id"],"invoice":purchase_id,"reason":reason,"total":float(total)})
                return_id=int(s.execute(text("SELECT last_insert_rowid()")).scalar())

                for item_id,pid,qty,cost,line,line_tax in prepared:
                    s.execute(text("""
                        INSERT INTO purchase_return_items
                        (return_id,purchase_invoice_item_id,product_id,quantity,unit_cost,line_total)
                        VALUES(:return,:item,:product,:quantity,:cost,:line)
                    """),{"return":return_id,"item":item_id,"product":pid,"quantity":float(qty),"cost":float(cost),"line":float(line)})

                    changed=s.execute(text("""
                        UPDATE stock_balances
                        SET quantity=quantity-:qty,last_movement_at=CURRENT_TIMESTAMP
                        WHERE product_id=:product AND warehouse_id=:warehouse
                          AND quantity>=:qty
                    """),{"qty":float(qty),"product":pid,"warehouse":wh})
                    if changed.rowcount!=1: raise ValueError(f"المخزون غير كافٍ لتنفيذ إرجاع الصنف {pid}")

                    mc=cls._columns(s,"stock_movements")
                    fields=["product_id","warehouse_id","quantity"]; values=[":product",":warehouse",":quantity"]
                    params={"product":pid,"warehouse":wh,"quantity":-float(qty)}
                    for col,val in [("movement_type","PURCHASE_RETURN"),("unit_cost",float(cost)),("reference_type","PURCHASE_RETURN"),("reference_id",return_id),("notes",reason)]:
                        if col in mc: fields.append(col); values.append(":"+col); params[col]=val
                    if "created_at" in mc: fields.append("created_at"); values.append("CURRENT_TIMESTAMP")
                    s.execute(text(f"INSERT INTO stock_movements({','.join(fields)}) VALUES({','.join(values)})"),params)

                supplier_account=AccountingService.get_account_id(s,"2100")
                inventory_account=AccountingService.get_account_id(s,"1400")
                vat_input=AccountingService.get_account_id(s,"1500") if tax>0 else None
                settlement= supplier_account if refund_method=="credit" else AccountingService.get_account_id(s,AccountingService.PAYMENT_ACCOUNTS.get(refund_method,"1100"))
                lines=[{"account_id":settlement,"debit":total,"credit":Decimal("0"),"description":f"تسوية مرتجع مشتريات {return_number}"},
                       {"account_id":inventory_account,"debit":Decimal("0"),"credit":subtotal,"description":f"إخراج مخزون مرتجع {return_number}"}]
                if tax>0: lines.append({"account_id":vat_input,"debit":Decimal("0"),"credit":tax,"description":f"عكس ضريبة مدخلات {return_number}"})
                accounting=AccountingService._post_lines(s,AccountingService.next_entry_number(s),f"ترحيل مرتجع مشتريات {return_number}","PURCHASE_RETURN",return_id,lines)

                if refund_method=="credit":
                    supplier_cols = {r[1] for r in s.connection().exec_driver_sql("PRAGMA table_info(suppliers)").fetchall()}
                    set_parts = ["current_balance=COALESCE(current_balance,0)-:amount"]
                    if "updated_at" in supplier_cols:
                        set_parts.append("updated_at=CURRENT_TIMESTAMP")
                    s.execute(text(f"UPDATE suppliers SET {','.join(set_parts)} WHERE id=:id"),
                              {"amount": float(total), "id": invoice["supplier_id"]})

                AuditService.log(s,"PURCHASE_RETURN_POSTED","purchase_return",return_id)
                s.commit()
                return {"id":return_id,"return_number":return_number,"purchase_id":purchase_id,
                        "subtotal":float(subtotal),"tax":float(tax),"total":float(total),
                        "journal_entry_id":accounting["journal_entry_id"],"journal_entry_number":accounting["entry_number"]}
            except Exception:
                s.rollback()
                raise
