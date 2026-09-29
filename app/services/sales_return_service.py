from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import text
from app.database.connection import get_session
from app.services.audit_service import AuditService
from app.services.accounting_service import AccountingService
from app.services.document_number_service import DocumentNumberService


class SalesReturnService:
    """مرتجع مبيعات متكامل: منع تجاوز الكمية، استعادة المخزون، تسوية وسيلة الدفع والمحاسبة."""

    @staticmethod
    def money(value):
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @classmethod
    def _ensure_schema(cls, s):
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS sales_returns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_id INTEGER NOT NULL,
                return_number VARCHAR(100) NOT NULL UNIQUE,
                subtotal NUMERIC NOT NULL DEFAULT 0,
                tax_amount NUMERIC NOT NULL DEFAULT 0,
                total_amount NUMERIC NOT NULL DEFAULT 0,
                reason TEXT NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'POSTED',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """))
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS sales_return_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                return_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity NUMERIC NOT NULL,
                unit_price NUMERIC NOT NULL DEFAULT 0,
                discount_amount NUMERIC NOT NULL DEFAULT 0,
                tax_amount NUMERIC NOT NULL DEFAULT 0,
                line_total NUMERIC NOT NULL DEFAULT 0
            )
        """))

    @classmethod
    def create_return(cls, sale_id, items, reason, refund_method=None):
        if not items or not reason or not str(reason).strip():
            raise ValueError("بنود المرتجع والسبب مطلوبان")
        with get_session() as s:
            try:
                cls._ensure_schema(s)
                sale = s.execute(
                    text("SELECT * FROM sales WHERE id=:id"),
                    {"id": sale_id},
                ).fetchone()
                if not sale:
                    raise ValueError("فاتورة البيع غير موجودة")
                if getattr(sale, "status", None) in ("VOID", "CANCELLED"):
                    raise ValueError("لا يمكن إرجاع فاتورة ملغاة")

                rows = s.execute(text("""
                    SELECT si.product_id, si.quantity, si.unit_price,
                           COALESCE(si.discount_amount, si.discount, 0) AS discount_amount,
                           COALESCE(si.tax_amount, 0) AS tax_amount
                    FROM sale_items si
                    WHERE si.sale_id=:sale
                    ORDER BY si.id
                """), {"sale": sale_id}).fetchall()
                originals = {int(r.product_id): r for r in rows}
                if not originals:
                    raise ValueError("فاتورة البيع لا تحتوي أصنافاً")

                prepared = []
                subtotal = Decimal("0")
                tax = Decimal("0")
                for item in items:
                    pid = int(item["product_id"])
                    qty = Decimal(str(item["quantity"]))
                    if qty <= 0:
                        raise ValueError("كمية المرتجع يجب أن تكون موجبة")
                    original = originals.get(pid)
                    if not original:
                        raise ValueError(f"الصنف {pid} غير موجود في الفاتورة")

                    already = Decimal(str(s.execute(text("""
                        SELECT COALESCE(SUM(sri.quantity),0)
                        FROM sales_return_items sri
                        JOIN sales_returns sr ON sr.id=sri.return_id
                        WHERE sr.sale_id=:sale AND sri.product_id=:product
                          AND sr.status<>'VOID'
                    """), {"sale": sale_id, "product": pid}).scalar() or 0))
                    original_qty = Decimal(str(original.quantity or 0))
                    if qty + already > original_qty:
                        raise ValueError(f"الكمية المرتجعة أكبر من المتاح للصنف {pid}")

                    unit = Decimal(str(original.unit_price or 0))
                    discount_total = Decimal(str(original.discount_amount or 0))
                    original_line = (original_qty * unit) - discount_total
                    discount_per_unit = (discount_total / original_qty) if original_qty else Decimal("0")
                    line_discount = cls.money(discount_per_unit * qty)
                    line_subtotal = cls.money(qty * unit - line_discount)
                    tax_per_unit = Decimal(str(original.tax_amount or 0)) / original_qty if original_qty else Decimal("0")
                    line_tax = cls.money(tax_per_unit * qty)
                    subtotal += line_subtotal
                    tax += line_tax
                    prepared.append((pid, qty, unit, line_discount, line_tax, line_subtotal))

                subtotal = cls.money(subtotal)
                tax = cls.money(tax)
                total = cls.money(subtotal + tax)
                return_number = DocumentNumberService.next_number(s, "SALE_RETURN", "SR", 6)

                s.execute(text("""
                    INSERT INTO sales_returns
                    (sale_id,return_number,subtotal,tax_amount,total_amount,reason,status)
                    VALUES(:sale,:number,:subtotal,:tax,:total,:reason,'POSTED')
                """), {
                    "sale": sale_id, "number": return_number,
                    "subtotal": float(subtotal), "tax": float(tax),
                    "total": float(total), "reason": str(reason).strip()
                })
                return_id = int(s.execute(text("SELECT last_insert_rowid()")).scalar())

                warehouse = int(getattr(sale, "warehouse_id", 1) or 1)
                for pid, qty, unit, discount, line_tax, line_total in prepared:
                    s.execute(text("""
                        INSERT INTO sales_return_items
                        (return_id,product_id,quantity,unit_price,discount_amount,tax_amount,line_total)
                        VALUES(:return,:product,:quantity,:unit,:discount,:tax,:line)
                    """), {
                        "return": return_id, "product": pid, "quantity": float(qty),
                        "unit": float(unit), "discount": float(discount),
                        "tax": float(line_tax), "line": float(line_total)
                    })
                    changed = s.execute(text("""
                        UPDATE stock
                        SET quantity=quantity+:q,
                            available_quantity=available_quantity+:q,
                            updated_at=CURRENT_TIMESTAMP
                        WHERE product_id=:product AND warehouse_id=:warehouse
                    """), {"q": float(qty), "product": pid, "warehouse": warehouse})
                    if changed.rowcount != 1:
                        raise ValueError(f"لا يوجد رصيد مخزون للصنف {pid}")

                    cols = {r[1] for r in s.execute(text("PRAGMA table_info(stock_movements)")).fetchall()}
                    fields = ["product_id", "warehouse_id", "quantity"]
                    values = [":product", ":warehouse", ":quantity"]
                    params = {"product": pid, "warehouse": warehouse, "quantity": float(qty)}
                    for col, val in [
                        ("movement_type", "SALE_RETURN"),
                        ("unit_cost", 0),
                        ("reference_type", "SALE_RETURN"),
                        ("reference_id", return_id),
                        ("notes", str(reason)),
                    ]:
                        if col in cols:
                            fields.append(col); values.append(":"+col); params[col] = val
                    if "created_at" in cols:
                        fields.append("created_at"); values.append("CURRENT_TIMESTAMP")
                    s.execute(text(f"INSERT INTO stock_movements({','.join(fields)}) VALUES({','.join(values)})"), params)

                # توزيع مبلغ الرد على وسائل الدفع الأصلية، بما فيها الجزء الآجل.
                payments = s.execute(text("""
                    SELECT payment_method, COALESCE(SUM(amount),0) amount
                    FROM sale_payments
                    WHERE sale_id=:sale
                    GROUP BY payment_method
                """), {"sale": sale_id}).fetchall()
                components = [(str(r.payment_method), Decimal(str(r.amount or 0))) for r in payments if Decimal(str(r.amount or 0)) > 0]
                due = Decimal(str(getattr(sale, "due_amount", 0) or 0))
                if due > 0:
                    components.append(("credit", due))
                original_total = sum((x[1] for x in components), Decimal("0"))
                if original_total <= 0:
                    components = [("cash", total)]
                    original_total = total

                requested = refund_method
                if requested:
                    components = [(requested, total)]

                allocations = []
                remaining = total
                for i, (method, amount) in enumerate(components):
                    if i == len(components) - 1:
                        part = remaining
                    else:
                        part = cls.money(total * amount / original_total)
                        if part > remaining:
                            part = remaining
                    if part > 0:
                        allocations.append((method, part))
                        remaining -= part

                sales_account = AccountingService.get_account_id(s, "4100")
                vat_account = AccountingService.get_account_id(s, "2200")
                customer_account = AccountingService.get_account_id(s, "1300")
                inventory_account = AccountingService.get_account_id(s, "1400")
                cogs_account = AccountingService.get_account_id(s, "5100")

                journal_lines = [
                    (sales_account, subtotal, Decimal("0"), "عكس إيراد مرتجع مبيعات"),
                    (vat_account, tax, Decimal("0"), "عكس ضريبة مخرجات مرتجع"),
                ]
                for method, amount in allocations:
                    if method == "credit":
                        account = customer_account
                        if getattr(sale, "customer_id", None):
                            current = Decimal(str(s.execute(
                                text("SELECT COALESCE(current_balance,0) FROM customers WHERE id=:id"),
                                {"id": int(sale.customer_id)}
                            ).scalar() or 0))
                            new_balance = current - amount
                            if new_balance < 0:
                                raise ValueError("رصيد العميل لا يسمح بتسوية مرتجع بهذا المبلغ")
                            s.execute(text("""
                                UPDATE customers SET current_balance=:balance,
                                    updated_at=CURRENT_TIMESTAMP WHERE id=:id
                            """), {"balance": float(new_balance), "id": int(sale.customer_id)})
                        else:
                            raise ValueError("لا يمكن رد الجزء الآجل دون عميل")
                    else:
                        code = AccountingService.PAYMENT_ACCOUNTS.get(method, "1100")
                        account = AccountingService.get_account_id(s, code)
                    journal_lines.append((account, Decimal("0"), amount, f"رد قيمة المرتجع - {method}"))

                # إعادة تكلفة المخزون: نستخدم متوسط التكلفة الحالي كحل متوافق مع المخزون الحالي.
                cogs = Decimal("0")
                for pid, qty, *_ in prepared:
                    cost = Decimal(str(s.execute(text("""
                        SELECT COALESCE(average_cost,0) FROM stock
                        WHERE product_id=:product AND warehouse_id=:warehouse LIMIT 1
                    """), {"product": pid, "warehouse": warehouse}).scalar() or 0))
                    cogs += cls.money(cost * qty)
                if cogs > 0:
                    journal_lines.extend([
                        (inventory_account, cogs, Decimal("0"), "إعادة تكلفة المخزون"),
                        (cogs_account, Decimal("0"), cogs, "عكس تكلفة البضاعة المباعة"),
                    ])

                debit = cls.money(sum((x[1] for x in journal_lines), Decimal("0")))
                credit = cls.money(sum((x[2] for x in journal_lines), Decimal("0")))
                if debit != credit:
                    raise ValueError(f"قيد المرتجع غير متوازن: {debit} مقابل {credit}")

                entry_number = AccountingService.next_entry_number(s)
                s.execute(text("""
                    INSERT INTO journal_entries
                    (entry_number,entry_date,description,source_type,source_id,status,
                     fiscal_period_id,created_by,created_at)
                    VALUES(:number,CURRENT_DATE,:description,'SALE_RETURN',:source,'POSTED',
                           NULL,NULL,CURRENT_TIMESTAMP)
                """), {
                    "number": entry_number,
                    "description": f"ترحيل مرتجع {return_number}",
                    "source": return_id
                })
                entry_id = int(s.execute(text("SELECT last_insert_rowid()")).scalar())
                for account, debit, credit, description in journal_lines:
                    s.execute(text("""
                        INSERT INTO journal_entry_lines
                        (journal_entry_id,account_id,cost_center_id,description,debit,credit)
                        VALUES(:entry,:account,NULL,:description,:debit,:credit)
                    """), {
                        "entry": entry_id, "account": int(account),
                        "description": description, "debit": float(debit), "credit": float(credit)
                    })

                AuditService.log(s, "SALE_RETURN_POSTED", "sale_return", return_id)
                s.commit()
                return {
                    "id": return_id, "return_number": return_number,
                    "sale_id": sale_id, "subtotal": float(subtotal),
                    "tax": float(tax), "total": float(total),
                    "journal_entry_id": entry_id
                }
            except Exception:
                s.rollback()
                raise
