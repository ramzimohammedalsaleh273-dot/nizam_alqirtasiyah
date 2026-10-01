from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import text
from app.database.connection import get_session
from app.services.accounting_service import AccountingService
from app.services.audit_service import AuditService
from app.services.document_number_service import DocumentNumberService
from app.services.permission_service import PermissionService


class SalesReturnService:
    """مرتجع مبيعات متكامل مرتبط بالجداول المرجعية الفعلية للنظام."""

    @staticmethod
    def money(value):
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def _columns(session, table):
        return {r[1] for r in session.connection().exec_driver_sql(f"PRAGMA table_info({table})").fetchall()}

    @classmethod
    def _ensure_schema(cls, s):
        # جدول بنود المرتجع جزء من النموذج المرجعي، ويُنشأ فقط إذا لم يكن موجودًا.
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS sale_return_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                return_id INTEGER NOT NULL,
                sale_item_id INTEGER NULL,
                product_id INTEGER NOT NULL,
                quantity NUMERIC NOT NULL,
                unit_price NUMERIC NOT NULL DEFAULT 0,
                total_amount NUMERIC NOT NULL DEFAULT 0
            )
        """))

    @classmethod
    def create_return(cls, sale_id, items, reason, refund_method=None, user_id=None):
        if not items or not str(reason or "").strip():
            raise ValueError("بنود المرتجع والسبب مطلوبان")

        with get_session() as s:
            try:
                PermissionService.ensure_schema(s)
                if user_id is None or not PermissionService.has_in_session(s, user_id, "sale.return.create"):
                    raise PermissionError("لا توجد صلاحية لتنفيذ المرتجع")
                cls._ensure_schema(s)
                sale = s.execute(text("SELECT * FROM sales WHERE id=:id"), {"id": sale_id}).mappings().first()
                if not sale:
                    raise ValueError("فاتورة البيع غير موجودة")
                if str(sale.get("status") or "").upper() in {"VOID", "CANCELLED"}:
                    raise ValueError("لا يمكن إرجاع فاتورة ملغاة")

                rows = s.execute(text("""
                    SELECT si.id AS sale_item_id, si.product_id, si.quantity,
                           si.unit_price,
                           COALESCE(si.discount_amount,0) AS discount_amount,
                           COALESCE(si.tax_amount,0) AS tax_amount,
                           COALESCE(si.line_total,0) AS line_total
                    FROM sale_items si
                    WHERE si.sale_id=:sale
                    ORDER BY si.id
                """), {"sale": sale_id}).mappings().all()
                originals = {int(r["product_id"]): r for r in rows}
                if not originals:
                    raise ValueError("فاتورة البيع لا تحتوي أصنافًا")

                prepared=[]
                total=Decimal("0")
                for item in items:
                    pid=int(item["product_id"])
                    qty=Decimal(str(item["quantity"]))
                    if qty <= 0:
                        raise ValueError("كمية المرتجع يجب أن تكون موجبة")
                    original=originals.get(pid)
                    if not original:
                        raise ValueError(f"الصنف {pid} غير موجود في الفاتورة")

                    already=Decimal(str(s.execute(text("""
                        SELECT COALESCE(SUM(sri.quantity),0)
                        FROM sale_return_items sri
                        JOIN sale_returns sr ON sr.id=sri.return_id
                        WHERE sr.sale_id=:sale AND sri.product_id=:product
                          AND UPPER(COALESCE(sr.status,'')) NOT IN ('VOID','CANCELLED')
                    """), {"sale":sale_id,"product":pid}).scalar() or 0))
                    original_qty=Decimal(str(original["quantity"] or 0))
                    if qty + already > original_qty:
                        raise ValueError(f"الكمية المرتجعة أكبر من المتاح للصنف {pid}")

                    unit=Decimal(str(original["unit_price"] or 0))
                    discount=Decimal(str(original["discount_amount"] or 0))
                    tax=Decimal(str(original["tax_amount"] or 0))
                    discount_per_unit=(discount/original_qty) if original_qty else Decimal("0")
                    tax_per_unit=(tax/original_qty) if original_qty else Decimal("0")
                    line_total=cls.money(qty * unit - discount_per_unit*qty + tax_per_unit*qty)
                    total += line_total
                    prepared.append({
                        "sale_item_id":int(original["sale_item_id"]),
                        "product_id":pid,
                        "quantity":qty,
                        "unit_price":unit,
                        "line_total":line_total,
                        "tax":cls.money(tax_per_unit*qty),
                        "subtotal":cls.money(qty*unit-discount_per_unit*qty),
                    })

                total=cls.money(total)
                return_number=DocumentNumberService.next_number(s,"SALE_RETURN","SR",6)
                customer_id=sale.get("customer_id")
                created_by=sale.get("cashier_id")

                s.execute(text("""
                    INSERT INTO sale_returns
                    (return_number,sale_id,customer_id,reason,status,total_amount,created_by,created_at)
                    VALUES(:number,:sale,:customer,:reason,'POSTED',:total,:created_by,CURRENT_TIMESTAMP)
                """), {
                    "number":return_number,"sale":sale_id,"customer":customer_id,
                    "reason":str(reason).strip(),"total":float(total),"created_by":created_by
                })
                return_id=int(s.execute(text("SELECT last_insert_rowid()")).scalar())

                warehouse=int(sale.get("warehouse_id") or 1)
                for item in prepared:
                    s.execute(text("""
                        INSERT INTO sale_return_items
                        (return_id,sale_item_id,product_id,quantity,unit_price,total_amount)
                        VALUES(:return,:sale_item,:product,:quantity,:unit,:total)
                    """), {
                        "return":return_id,"sale_item":item["sale_item_id"],"product":item["product_id"],
                        "quantity":float(item["quantity"]),"unit":float(item["unit_price"]),
                        "total":float(item["line_total"])
                    })

                    changed=s.execute(text("""
                        UPDATE stock_balances
                        SET quantity=quantity+:q,last_movement_at=CURRENT_TIMESTAMP
                        WHERE product_id=:product AND warehouse_id=:warehouse
                    """), {"q":float(item["quantity"]),"product":item["product_id"],"warehouse":warehouse})
                    if changed.rowcount != 1:
                        raise ValueError(f"لا يوجد رصيد مخزون للصنف {item['product_id']} في المستودع المحدد")

                    mc=cls._columns(s,"stock_movements")
                    fields=["product_id","warehouse_id","quantity"]
                    values=[":product",":warehouse",":quantity"]
                    params={"product":item["product_id"],"warehouse":warehouse,"quantity":float(item["quantity"])}
                    for col,val in [
                        ("movement_type","SALE_RETURN"),("unit_cost",0),("reference_type","SALE_RETURN"),
                        ("reference_id",return_id),("notes",str(reason).strip())
                    ]:
                        if col in mc:
                            fields.append(col); values.append(":"+col); params[col]=val
                    if "created_at" in mc:
                        fields.append("created_at"); values.append("CURRENT_TIMESTAMP")
                    s.execute(text(f"INSERT INTO stock_movements({','.join(fields)}) VALUES({','.join(values)})"),params)

                payments=s.execute(text("""
                    SELECT payment_method,COALESCE(SUM(amount),0) AS amount
                    FROM sale_payments WHERE sale_id=:sale GROUP BY payment_method
                """),{"sale":sale_id}).mappings().all()
                components=[(str(x["payment_method"]),Decimal(str(x["amount"] or 0))) for x in payments if Decimal(str(x["amount"] or 0))>0]
                due=Decimal(str(sale.get("due_amount") or 0))
                if due>0: components.append(("credit",due))
                original_total=sum((x[1] for x in components),Decimal("0"))
                if original_total<=0: components=[("cash",total)]; original_total=total
                if refund_method: components=[(refund_method,total)]; original_total=total

                allocations=[]; remaining=total
                for i,(method,amount) in enumerate(components):
                    part=remaining if i==len(components)-1 else cls.money(total*amount/original_total)
                    part=min(part,remaining)
                    if part>0:
                        allocations.append((method,part)); remaining-=part

                sales_account=AccountingService.get_account_id(s,"4100")
                vat_account=AccountingService.get_account_id(s,"2200")
                customer_account=AccountingService.get_account_id(s,"1300")
                inventory_account=AccountingService.get_account_id(s,"1400")
                cogs_account=AccountingService.get_account_id(s,"5100")

                subtotal=cls.money(sum((x["subtotal"] for x in prepared),Decimal("0")))
                tax=cls.money(sum((x["tax"] for x in prepared),Decimal("0")))
                journal_lines=[(sales_account,subtotal,Decimal("0"),"عكس إيراد مرتجع مبيعات"),
                               (vat_account,tax,Decimal("0"),"عكس ضريبة مخرجات مرتجع")]
                for method,amount in allocations:
                    if method=="credit":
                        if not customer_id: raise ValueError("لا يمكن رد الجزء الآجل دون عميل")
                        current=Decimal(str(s.execute(text("SELECT COALESCE(current_balance,0) FROM customers WHERE id=:id"),{"id":int(customer_id)}).scalar() or 0))
                        new_balance=current-amount
                        if new_balance<0: raise ValueError("رصيد العميل لا يسمح بتسوية هذا المرتجع")
                        s.execute(text("UPDATE customers SET current_balance=:balance,updated_at=CURRENT_TIMESTAMP WHERE id=:id"),{"balance":float(new_balance),"id":int(customer_id)})
                        account=customer_account
                    else:
                        account=AccountingService.get_account_id(s,AccountingService.PAYMENT_ACCOUNTS.get(method,"1100"))
                    journal_lines.append((account,Decimal("0"),amount,f"رد قيمة المرتجع - {method}"))

                cogs=Decimal("0")
                for item in prepared:
                    cost=Decimal(str(s.execute(text("""
                        SELECT COALESCE(average_cost,0) FROM stock_balances
                        WHERE product_id=:product AND warehouse_id=:warehouse LIMIT 1
                    """),{"product":item["product_id"],"warehouse":warehouse}).scalar() or 0))
                    cogs += cls.money(cost*item["quantity"])
                if cogs>0:
                    journal_lines.extend([(inventory_account,cogs,Decimal("0"),"إعادة تكلفة المخزون"),
                                          (cogs_account,Decimal("0"),cogs,"عكس تكلفة البضاعة المباعة")])

                debit=cls.money(sum((x[1] for x in journal_lines),Decimal("0")))
                credit=cls.money(sum((x[2] for x in journal_lines),Decimal("0")))
                if debit!=credit: raise ValueError(f"قيد المرتجع غير متوازن: {debit} مقابل {credit}")

                entry_number=AccountingService.next_entry_number(s)
                s.execute(text("""
                    INSERT INTO journal_entries
                    (entry_number,entry_date,description,source_type,source_id,status,fiscal_period_id,created_by,created_at)
                    VALUES(:number,CURRENT_DATE,:description,'SALE_RETURN',:source,'POSTED',NULL,:created_by,CURRENT_TIMESTAMP)
                """),{"number":entry_number,"description":f"ترحيل مرتجع {return_number}","source":return_id,"created_by":created_by})
                entry_id=int(s.execute(text("SELECT last_insert_rowid()")).scalar())
                for account,debit_value,credit_value,description in journal_lines:
                    s.execute(text("""
                        INSERT INTO journal_entry_lines
                        (journal_entry_id,account_id,cost_center_id,description,debit,credit)
                        VALUES(:entry,:account,NULL,:description,:debit,:credit)
                    """),{"entry":entry_id,"account":int(account),"description":description,"debit":float(debit_value),"credit":float(credit_value)})

                AuditService.log(s,"SALE_RETURN_POSTED","sale_return",return_id)
                s.commit()
                return {"id":return_id,"return_number":return_number,"sale_id":sale_id,
                        "subtotal":float(subtotal),"tax":float(tax),"total":float(total),
                        "journal_entry_id":entry_id}
            except Exception:
                s.rollback()
                raise
