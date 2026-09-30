from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import text
from app.database.connection import get_session
from app.services.accounting_service import AccountingService
from app.services.audit_service import AuditService
from app.services.document_number_service import DocumentNumberService


class PurchaseReturnService:
    """إرجاع مشتريات حقيقي: مخزون + مورد/خزينة + ضريبة + قيد محاسبي + تدقيق."""

    @staticmethod
    def money(value):
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def _columns(session, table):
        return {r[1] for r in session.connection().exec_driver_sql(
            f"PRAGMA table_info({table})"
        ).fetchall()}

    @classmethod
    def create_return(cls, purchase_id, items, reason="إرجاع مشتريات",
                      refund_method="credit", warehouse_id=None):
        if not items:
            raise ValueError("لا توجد أصناف للإرجاع")
        if refund_method not in {"credit", "cash", "bank", "bank_transfer", "card"}:
            raise ValueError("طريقة التسوية غير مدعومة")

        with get_session() as s:
            try:
                s.execute(text("""
                    CREATE TABLE IF NOT EXISTS purchase_returns (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        purchase_id INTEGER NOT NULL,
                        supplier_id INTEGER NULL,
                        warehouse_id INTEGER NULL,
                        return_number VARCHAR(100) NOT NULL UNIQUE,
                        subtotal NUMERIC NOT NULL DEFAULT 0,
                        tax_amount NUMERIC NOT NULL DEFAULT 0,
                        total_amount NUMERIC NOT NULL DEFAULT 0,
                        refund_method VARCHAR(30) NOT NULL DEFAULT 'credit',
                        status VARCHAR(30) NOT NULL DEFAULT 'POSTED',
                        reason TEXT NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                s.execute(text("""
                    CREATE TABLE IF NOT EXISTS purchase_return_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        return_id INTEGER NOT NULL,
                        product_id INTEGER NOT NULL,
                        quantity NUMERIC NOT NULL,
                        unit_cost NUMERIC NOT NULL DEFAULT 0,
                        line_total NUMERIC NOT NULL DEFAULT 0
                    )
                """))
                invoice = s.execute(text(
                    "SELECT * FROM purchase_invoices WHERE id=:id LIMIT 1"
                ), {"id": purchase_id}).fetchone()
                if not invoice:
                    raise ValueError("فاتورة الشراء غير موجودة")

                inv = dict(invoice._mapping)
                if str(inv.get("status", "POSTED")).upper() in {"VOID", "CANCELLED"}:
                    raise ValueError("لا يمكن إرجاع فاتورة ملغاة")

                ic = cls._columns(s, "purchase_invoice_items")
                fk = "invoice_id" if "invoice_id" in ic else (
                    "purchase_invoice_id" if "purchase_invoice_id" in ic else None
                )
                if not fk:
                    raise ValueError("جدول بنود المشتريات لا يحتوي مفتاح الفاتورة")

                wh = warehouse_id or inv.get("warehouse_id") or 1
                rows = s.execute(text(f"""
                    SELECT pii.*, p.name_ar
                    FROM purchase_invoice_items pii
                    JOIN products p ON p.id=pii.product_id
                    WHERE pii.{fk}=:id
                    ORDER BY pii.id
                """), {"id": purchase_id}).fetchall()
                originals = {int(r.product_id): dict(r._mapping) for r in rows}

                prepared = []
                subtotal = Decimal("0")
                for item in items:
                    pid = int(item["product_id"])
                    qty = Decimal(str(item["quantity"]))
                    if qty <= 0:
                        raise ValueError("كمية الإرجاع يجب أن تكون أكبر من صفر")
                    original = originals.get(pid)
                    if not original:
                        raise ValueError(f"الصنف غير موجود في الفاتورة: {pid}")
                    original_qty = Decimal(str(original.get("quantity") or 0))
                    already = Decimal(str(s.execute(text("""
                        SELECT COALESCE(SUM(pri.quantity),0)
                        FROM purchase_return_items pri
                        JOIN purchase_returns pr ON pr.id=pri.return_id
                        WHERE pr.purchase_id=:purchase_id
                          AND pri.product_id=:product_id
                          AND pr.status<>'VOID'
                    """), {"purchase_id": purchase_id, "product_id": pid}).scalar() or 0))
                    if qty + already > original_qty:
                        raise ValueError(f"الكمية المرتجعة أكبر من الكمية المسموح بها للصنف: {original.get('name_ar')}")
                    cost = Decimal(str(original.get("unit_cost") or 0))
                    line = cls.money(qty * cost)
                    subtotal += line
                    prepared.append((pid, qty, cost, line))

                subtotal = cls.money(subtotal)
                invoice_subtotal = cls.money(inv.get("subtotal") or 0)
                invoice_tax = cls.money(inv.get("tax_amount") or 0)
                tax_rate = (invoice_tax / invoice_subtotal) if invoice_subtotal > 0 else Decimal("0")
                tax = cls.money(subtotal * tax_rate)
                total = cls.money(subtotal + tax)

                rc = cls._columns(s, "purchase_returns")
                required = {"purchase_id", "return_number", "subtotal", "tax_amount",
                            "total_amount", "refund_method", "status", "reason"}
                if not required.issubset(rc):
                    missing = ", ".join(sorted(required - rc))
                    raise ValueError(f"جدول مرتجعات المشتريات غير مكتمل، الحقول المفقودة: {missing}")

                return_number = DocumentNumberService.next_number(s, "PURCHASE_RETURN", "PR", 6)
                fields = ["purchase_id", "return_number", "subtotal", "tax_amount",
                          "total_amount", "refund_method", "status", "reason"]
                values = [":purchase_id", ":return_number", ":subtotal", ":tax_amount",
                          ":total_amount", ":refund_method", "'POSTED'", ":reason"]
                params = {
                    "purchase_id": purchase_id, "return_number": return_number,
                    "subtotal": float(subtotal), "tax_amount": float(tax),
                    "total_amount": float(total), "refund_method": refund_method,
                    "reason": reason
                }
                if "warehouse_id" in rc:
                    fields.append("warehouse_id"); values.append(":warehouse_id"); params["warehouse_id"] = wh
                if "supplier_id" in rc and inv.get("supplier_id") is not None:
                    fields.append("supplier_id"); values.append(":supplier_id"); params["supplier_id"] = inv["supplier_id"]
                if "created_at" in rc:
                    fields.append("created_at"); values.append("CURRENT_TIMESTAMP")
                s.execute(text(f"INSERT INTO purchase_returns({','.join(fields)}) VALUES({','.join(values)})"), params)
                return_id = int(s.execute(text("SELECT last_insert_rowid()")).scalar())

                prc = cls._columns(s, "purchase_return_items")
                for pid, qty, cost, line in prepared:
                    f = ["return_id", "product_id", "quantity", "unit_cost"]
                    v = [":return_id", ":product_id", ":quantity", ":unit_cost"]
                    p = {"return_id": return_id, "product_id": pid, "quantity": float(qty), "unit_cost": float(cost)}
                    if "line_total" in prc:
                        f.append("line_total"); v.append(":line_total"); p["line_total"] = float(line)
                    s.execute(text(f"INSERT INTO purchase_return_items({','.join(f)}) VALUES({','.join(v)})"), p)

                    stock = s.execute(text("""
                        SELECT id, quantity, available_quantity
                        FROM stock
                        WHERE product_id=:product AND warehouse_id=:warehouse
                        LIMIT 1
                    """), {"product": pid, "warehouse": wh}).fetchone()
                    if not stock or Decimal(str(stock.quantity or 0)) < qty:
                        raise ValueError("المخزون غير كافٍ لتنفيذ إرجاع المشتريات")
                    s.execute(text("""
                        UPDATE stock
                        SET quantity=quantity-:qty,
                            available_quantity=available_quantity-:qty,
                            updated_at=CURRENT_TIMESTAMP
                        WHERE id=:id AND quantity>=:qty AND available_quantity>=:qty
                    """), {"qty": float(qty), "id": stock.id})
                    if s.execute(text("SELECT changes()")).scalar() != 1:
                        raise ValueError("فشل تحديث المخزون أثناء الإرجاع")

                    mc = cls._columns(s, "stock_movements")
                    if {"product_id", "warehouse_id", "quantity"}.issubset(mc):
                        f = ["product_id", "warehouse_id", "quantity"]
                        v = [":product", ":warehouse", ":quantity"]
                        p = {"product": pid, "warehouse": wh, "quantity": -float(qty)}
                        for c, val in [
                            ("movement_type", "PURCHASE_RETURN"),
                            ("unit_cost", float(cost)),
                            ("reference_type", "PURCHASE_RETURN"),
                            ("reference_id", return_id),
                            ("notes", reason),
                        ]:
                            if c in mc:
                                f.append(c); v.append(":"+c); p[c] = val
                        if "created_at" in mc:
                            f.append("created_at"); v.append("CURRENT_TIMESTAMP")
                        s.execute(text(f"INSERT INTO stock_movements({','.join(f)}) VALUES({','.join(v)})"), p)

                supplier_id = inv.get("supplier_id")
                supplier_account = AccountingService.get_account_id(s, "2100")
                inventory_account = AccountingService.get_account_id(s, "1400")
                vat_input = AccountingService.get_account_id(s, "1500") if tax > 0 else None
                lines = [
                    {"account_id": supplier_account if refund_method == "credit" else AccountingService.get_account_id(
                        s, AccountingService.PAYMENT_ACCOUNTS.get(refund_method, "1100")
                    ), "debit": total, "credit": Decimal("0"),
                     "description": f"تسوية مرتجع مشتريات {return_number}"}
                ]
                lines.append({"account_id": inventory_account, "debit": Decimal("0"), "credit": subtotal,
                              "description": f"إخراج مخزون مرتجع {return_number}"})
                if tax > 0:
                    lines.append({"account_id": vat_input, "debit": Decimal("0"), "credit": tax,
                                  "description": f"عكس ضريبة مدخلات {return_number}"})

                accounting = AccountingService._post_lines(
                    s,
                    AccountingService.next_entry_number(s),
                    f"ترحيل مرتجع مشتريات {return_number}",
                    "PURCHASE_RETURN",
                    return_id,
                    lines,
                )
                if supplier_id and refund_method == "credit":
                    sc = cls._columns(s, "suppliers")
                    if "current_balance" in sc:
                        s.execute(text("""
                            UPDATE suppliers
                            SET current_balance=COALESCE(current_balance,0)-:amount,
                                updated_at=CURRENT_TIMESTAMP
                            WHERE id=:id
                        """), {"amount": float(total), "id": supplier_id})

                AuditService.log(s, "PURCHASE_RETURN_POSTED", "purchase_return", return_id)
                s.commit()
                return {
                    "id": return_id, "return_number": return_number,
                    "purchase_id": purchase_id, "subtotal": float(subtotal),
                    "tax": float(tax), "total": float(total),
                    "journal_entry_id": accounting["journal_entry_id"], "journal_entry_number": accounting["entry_number"]
                }
            except Exception:
                s.rollback()
                raise
