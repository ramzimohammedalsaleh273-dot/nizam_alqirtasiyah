from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import text
from app.database.connection import get_session
from app.services.accounting_service import AccountingService
from app.services.audit_service import AuditService
from app.services.permission_service import PermissionService


class PartyPaymentService:
    PAYMENT_ACCOUNTS = {"cash": "1100", "card": "1200", "bank": "1200", "bank_transfer": "1200"}

    @staticmethod
    def money(v):
        return Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def _cols(s, t):
        return {r[1] for r in s.connection().exec_driver_sql(f"PRAGMA table_info({t})").fetchall()}

    @classmethod
    def _ensure_payment_schema(cls, s, table):
        cols = cls._cols(s, table)
        if "cashier_session_id" not in cols:
            s.execute(text(f"ALTER TABLE {table} ADD COLUMN cashier_session_id INTEGER"))
        return cls._cols(s, table)

    @staticmethod
    def _active_cashier_session(s, cashier_id):
        if cashier_id is None:
            return None
        row = s.execute(
            text("""SELECT id FROM cashier_sessions
                    WHERE cashier_id=:c AND status='OPEN'
                    ORDER BY id DESC LIMIT 1"""),
            {"c": int(cashier_id)},
        ).fetchone()
        return int(row[0]) if row else None

    @classmethod
    def _journal(cls, s, source_type, source_id, description, debit_code, credit_code, amount):
        amount = cls.money(amount)
        da = AccountingService.get_account_id(s, debit_code)
        ca = AccountingService.get_account_id(s, credit_code)
        n = AccountingService.next_entry_number(s)
        s.execute(text("""
            INSERT INTO journal_entries
            (entry_number,entry_date,description,source_type,source_id,status,fiscal_period_id,created_by,created_at)
            VALUES(:n,CURRENT_DATE,:d,:t,:sid,'POSTED',NULL,NULL,CURRENT_TIMESTAMP)
        """), {"n": n, "d": description, "t": source_type, "sid": source_id})
        eid = int(s.execute(text("SELECT last_insert_rowid()")).scalar())
        for aid, debit, credit in (
            (da, amount, Decimal("0")),
            (ca, Decimal("0"), amount),
        ):
            s.execute(text("""
                INSERT INTO journal_entry_lines
                (journal_entry_id,account_id,cost_center_id,description,debit,credit)
                VALUES(:eid,:aid,NULL,:d,:debit,:credit)
            """), {
                "eid": eid, "aid": aid, "d": description,
                "debit": float(debit), "credit": float(credit),
            })
        return {"journal_entry_id": eid, "entry_number": n}

    @classmethod
    def receive_from_customer(
        cls, customer_id, amount, payment_method="cash",
        reference=None, notes=None, cashier_id=None,
    ):
        amount = cls.money(amount)
        if amount <= 0:
            raise ValueError("مبلغ التحصيل يجب أن يكون أكبر من صفر")
        if payment_method not in cls.PAYMENT_ACCOUNTS:
            raise ValueError("طريقة التحصيل غير مدعومة")

        with get_session() as s:
            try:
                PermissionService.ensure_schema(s)
                user_id = cashier_id
                if user_id is None:
                    user_id = s.execute(text("""
                        SELECT u.id
                        FROM users u
                        JOIN erp_user_roles ur ON ur.user_id=u.id
                        JOIN erp_roles r ON r.id=ur.role_id
                        WHERE COALESCE(r.is_active,1)=1
                        ORDER BY u.id LIMIT 1
                    """)).scalar()
                if not PermissionService.has_in_session(s, user_id, "treasury.receipt"):
                    raise PermissionError("لا توجد صلاحية لتحصيل مبالغ من العملاء")

                row = s.execute(
                    text("SELECT current_balance FROM customers WHERE id=:id"),
                    {"id": customer_id},
                ).fetchone()
                if not row:
                    raise ValueError("العميل غير موجود")
                old = cls.money(row[0] or 0)
                new = old - amount
                if new < 0:
                    raise ValueError("مبلغ التحصيل أكبر من رصيد العميل")

                cls._ensure_payment_schema(s, "customer_payments")
                session_id = cls._active_cashier_session(
                    s, cashier_id or user_id
                ) if payment_method == "cash" else None
                if payment_method == "cash" and session_id is None:
                    raise ValueError("يجب فتح جلسة كاشير قبل التحصيل النقدي")

                cols = cls._cols(s, "customer_payments")
                fields = ["customer_id", "amount"]
                vals = [":customer", ":amount"]
                p = {"customer": customer_id, "amount": float(amount)}
                for col, val in [
                    ("payment_method", payment_method),
                    ("reference_number", reference),
                    ("notes", notes),
                    ("cashier_session_id", session_id),
                ]:
                    if col in cols:
                        fields.append(col)
                        vals.append(":" + col)
                        p[col] = val
                if "created_at" in cols:
                    fields.append("created_at")
                    vals.append("CURRENT_TIMESTAMP")

                s.execute(
                    text(f"INSERT INTO customer_payments({','.join(fields)}) VALUES({','.join(vals)})"),
                    p,
                )
                payment_id = int(s.execute(text("SELECT last_insert_rowid()")).scalar())
                s.execute(
                    text("UPDATE customers SET current_balance=:b,updated_at=CURRENT_TIMESTAMP WHERE id=:id"),
                    {"b": float(new), "id": customer_id},
                )

                tables = {r[0] for r in s.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )).fetchall()}
                if "customer_transactions" in tables:
                    s.execute(text("""
                        INSERT INTO customer_transactions
                        (customer_id,transaction_type,amount,reference_type,reference_id,balance_after,created_at)
                        VALUES(:c,'PAYMENT',:a,'CUSTOMER_PAYMENT',:rid,:b,CURRENT_TIMESTAMP)
                    """), {
                        "c": customer_id, "a": float(amount),
                        "rid": payment_id, "b": float(new),
                    })

                journal = cls._journal(
                    s, "CUSTOMER_PAYMENT", payment_id, "تحصيل من العميل",
                    cls.PAYMENT_ACCOUNTS[payment_method], "1300", amount
                )
                AuditService.log(
                    s, "CUSTOMER_PAYMENT", "customer_payment",
                    payment_id, username=str(user_id)
                )
                s.commit()
                return {
                    "payment_id": payment_id, "customer_id": customer_id,
                    "amount": float(amount), "balance": float(new),
                    "cashier_session_id": session_id, "journal": journal,
                }
            except Exception:
                s.rollback()
                raise

    @classmethod
    def pay_supplier(
        cls, supplier_id, amount, payment_method="cash",
        reference=None, notes=None, cashier_id=None,
    ):
        amount = cls.money(amount)
        if amount <= 0:
            raise ValueError("مبلغ الدفع يجب أن يكون أكبر من صفر")
        if payment_method not in cls.PAYMENT_ACCOUNTS:
            raise ValueError("طريقة الدفع غير مدعومة")

        with get_session() as s:
            try:
                PermissionService.ensure_schema(s)
                user_id = cashier_id
                if user_id is None:
                    user_id = s.execute(text("""
                        SELECT u.id
                        FROM users u
                        JOIN erp_user_roles ur ON ur.user_id=u.id
                        JOIN erp_roles r ON r.id=ur.role_id
                        WHERE COALESCE(r.is_active,1)=1
                        ORDER BY u.id LIMIT 1
                    """)).scalar()
                if not PermissionService.has_in_session(s, user_id, "treasury.payment"):
                    raise PermissionError("لا توجد صلاحية لدفع مبالغ من الخزينة")

                row = s.execute(
                    text("SELECT current_balance FROM suppliers WHERE id=:id"),
                    {"id": supplier_id},
                ).fetchone()
                if not row:
                    raise ValueError("المورد غير موجود")
                old = cls.money(row[0] or 0)
                new = old - amount
                if new < 0:
                    raise ValueError("مبلغ الدفع أكبر من رصيد المورد")

                cls._ensure_payment_schema(s, "supplier_payments")
                session_id = cls._active_cashier_session(
                    s, cashier_id or user_id
                ) if payment_method == "cash" else None
                if payment_method == "cash" and session_id is None:
                    raise ValueError("يجب فتح جلسة كاشير قبل الدفع النقدي")

                cols = cls._cols(s, "supplier_payments")
                fields = ["supplier_id", "amount"]
                vals = [":supplier", ":amount"]
                p = {"supplier": supplier_id, "amount": float(amount)}
                for col, val in [
                    ("payment_method", payment_method),
                    ("reference_number", reference),
                    ("notes", notes),
                    ("cashier_session_id", session_id),
                ]:
                    if col in cols:
                        fields.append(col)
                        vals.append(":" + col)
                        p[col] = val
                if "created_at" in cols:
                    fields.append("created_at")
                    vals.append("CURRENT_TIMESTAMP")

                s.execute(
                    text(f"INSERT INTO supplier_payments({','.join(fields)}) VALUES({','.join(vals)})"),
                    p,
                )
                payment_id = int(s.execute(text("SELECT last_insert_rowid()")).scalar())
                s.execute(
                    text("UPDATE suppliers SET current_balance=:b,updated_at=CURRENT_TIMESTAMP WHERE id=:id"),
                    {"b": float(new), "id": supplier_id},
                )

                journal = cls._journal(
                    s, "SUPPLIER_PAYMENT", payment_id, "دفع للمورد",
                    "2100", cls.PAYMENT_ACCOUNTS[payment_method], amount
                )
                AuditService.log(
                    s, "SUPPLIER_PAYMENT", "supplier_payment",
                    payment_id, username=str(user_id)
                )
                s.commit()
                return {
                    "payment_id": payment_id, "supplier_id": supplier_id,
                    "amount": float(amount), "balance": float(new),
                    "cashier_session_id": session_id, "journal": journal,
                }
            except Exception:
                s.rollback()
                raise
