from decimal import Decimal
from sqlalchemy import text
from app.database.connection import get_session
from app.services.audit_service import AuditService


class CashierSessionService:
    @staticmethod
    def _ensure(s):
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS cashier_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cashier_id INTEGER,
                opening_amount NUMERIC(18,2) NOT NULL DEFAULT 0,
                closing_amount NUMERIC(18,2),
                expected_amount NUMERIC(18,2),
                difference NUMERIC(18,2),
                status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
                opened_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                closed_at DATETIME
            )
        """))

    @staticmethod
    def _cols(s, table):
        return {r[1] for r in s.connection().exec_driver_sql(f"PRAGMA table_info({table})").fetchall()}

    @classmethod
    def open(cls, cashier_id=None, opening_amount=0):
        amount = Decimal(str(opening_amount)).quantize(Decimal("0.01"))
        if amount < 0:
            raise ValueError("رصيد الافتتاح لا يمكن أن يكون سالبًا")
        with get_session() as s:
            cls._ensure(s)
            active = s.execute(text("""
                SELECT id FROM cashier_sessions
                WHERE status='OPEN' AND (cashier_id=:c OR (:c IS NULL AND cashier_id IS NULL))
                LIMIT 1
            """), {"c": cashier_id}).fetchone()
            if active:
                raise ValueError("لدى الكاشير جلسة مفتوحة بالفعل")
            sid = s.execute(text("""
                INSERT INTO cashier_sessions(cashier_id,opening_amount,status)
                VALUES(:c,:a,'OPEN')
            """), {"c": cashier_id, "a": float(amount)}).lastrowid
            AuditService.log(s, "CASHIER_SESSION_OPENED", "cashier_session", sid)
            s.commit()
            return int(sid)

    @classmethod
    def active_for(cls, cashier_id):
        with get_session() as s:
            cls._ensure(s)
            row = s.execute(text("""
                SELECT id FROM cashier_sessions
                WHERE cashier_id=:c AND status='OPEN'
                ORDER BY id DESC LIMIT 1
            """), {"c": int(cashier_id)}).fetchone()
            return int(row[0]) if row else None

    @classmethod
    def _movement_totals(cls, s, session_id, opened_at, cashier_id):
        sales_cash = Decimal(str(s.execute(text("""
            SELECT COALESCE(SUM(sp.amount),0)
            FROM sale_payments sp
            JOIN sales sl ON sl.id=sp.sale_id
            WHERE sp.payment_method='cash'
              AND sl.created_at>=:opened
              AND (sl.cashier_id=:cashier OR (:cashier IS NULL AND sl.cashier_id IS NULL))
              AND COALESCE(sl.status,'POSTED') NOT IN ('VOID','CANCELLED')
        """), {"opened": opened_at, "cashier": cashier_id}).scalar() or 0))

        receipt_cash = Decimal("0")
        if "customer_payments" in {r[0] for r in s.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )).fetchall()}:
            cols = cls._cols(s, "customer_payments")
            if "cashier_session_id" in cols:
                receipt_cash = Decimal(str(s.execute(text("""
                    SELECT COALESCE(SUM(amount),0) FROM customer_payments
                    WHERE payment_method='cash' AND cashier_session_id=:sid
                """), {"sid": session_id}).scalar() or 0))

        supplier_cash = Decimal("0")
        if "supplier_payments" in {r[0] for r in s.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )).fetchall()}:
            cols = cls._cols(s, "supplier_payments")
            if "cashier_session_id" in cols:
                supplier_cash = Decimal(str(s.execute(text("""
                    SELECT COALESCE(SUM(amount),0) FROM supplier_payments
                    WHERE payment_method='cash' AND cashier_session_id=:sid
                """), {"sid": session_id}).scalar() or 0))

        return sales_cash, receipt_cash, supplier_cash

    @classmethod
    def expected(cls, session_id):
        with get_session() as s:
            cls._ensure(s)
            row = s.execute(text("""
                SELECT opening_amount, cashier_id, opened_at, status
                FROM cashier_sessions WHERE id=:id
            """), {"id": session_id}).fetchone()
            if not row:
                raise ValueError("جلسة الكاشير غير موجودة")
            if row.status != "OPEN":
                raise ValueError("الجلسة مغلقة")
            sales_cash, receipt_cash, supplier_cash = cls._movement_totals(
                s, session_id, row.opened_at, row.cashier_id
            )
            expected = Decimal(str(row.opening_amount or 0)) + sales_cash + receipt_cash - supplier_cash
            return float(expected)

    @classmethod
    def close(cls, session_id, actual_amount):
        actual = Decimal(str(actual_amount)).quantize(Decimal("0.01"))
        if actual < 0:
            raise ValueError("النقد الفعلي لا يمكن أن يكون سالبًا")
        with get_session() as s:
            cls._ensure(s)
            row = s.execute(text("""
                SELECT opening_amount,cashier_id,opened_at,status
                FROM cashier_sessions WHERE id=:id
            """), {"id": session_id}).fetchone()
            if not row:
                raise ValueError("جلسة الكاشير غير موجودة")
            if row.status != "OPEN":
                raise ValueError("الجلسة مغلقة مسبقًا")

            sales_cash, receipt_cash, supplier_cash = cls._movement_totals(
                s, session_id, row.opened_at, row.cashier_id
            )
            expected = Decimal(str(row.opening_amount or 0)) + sales_cash + receipt_cash - supplier_cash
            difference = actual - expected

            s.execute(text("""
                UPDATE cashier_sessions SET closing_amount=:a,expected_amount=:e,
                difference=:d,status='CLOSED',closed_at=CURRENT_TIMESTAMP WHERE id=:id
            """), {
                "a": float(actual), "e": float(expected),
                "d": float(difference), "id": session_id,
            })
            AuditService.log(s, "CASHIER_SESSION_CLOSED", "cashier_session", session_id)
            s.commit()
            return {
                "session_id": session_id,
                "expected": float(expected),
                "actual": float(actual),
                "difference": float(difference),
                "sales_cash": float(sales_cash),
                "customer_receipts": float(receipt_cash),
                "supplier_payments": float(supplier_cash),
            }
