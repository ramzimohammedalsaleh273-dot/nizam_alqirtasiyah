from decimal import Decimal
from sqlalchemy import text
from app.database.connection import get_session
from app.services.audit_service import AuditService
from app.services.accounting_service import AccountingService

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

    @classmethod
    def open(cls,cashier_id=None,opening_amount=0):
        amount=Decimal(str(opening_amount)).quantize(Decimal("0.01"))
        if amount<0: raise ValueError("رصيد الافتتاح لا يمكن أن يكون سالبًا")
        with get_session() as s:
            cls._ensure(s)
            active=s.execute(text("SELECT id FROM cashier_sessions WHERE status='OPEN' AND (cashier_id=:c OR (:c IS NULL AND cashier_id IS NULL)) LIMIT 1"),{"c":cashier_id}).fetchone()
            if active: raise ValueError("لدى الكاشير جلسة مفتوحة بالفعل")
            sid=s.execute(text("""
                INSERT INTO cashier_sessions(cashier_id,opening_amount,status)
                VALUES(:c,:a,'OPEN')
            """),{"c":cashier_id,"a":float(amount)}).lastrowid
            s.commit()
            return int(sid)

    @classmethod
    def expected(cls,session_id):
        with get_session() as s:
            cls._ensure(s)
            row=s.execute(text("""
                SELECT opening_amount,
                       COALESCE((SELECT SUM(amount) FROM sale_payments sp
                                 JOIN sales sl ON sl.id=sp.sale_id
                                 WHERE sp.payment_method='cash'
                                 AND sl.created_at>=cs.opened_at
                                 AND cs.status='OPEN'),0)
                FROM cashier_sessions cs WHERE cs.id=:id
            """),{"id":session_id}).fetchone()
            if not row: raise ValueError("جلسة الكاشير غير موجودة")
            return float(Decimal(str(row[0] or 0))+Decimal(str(row[1] or 0)))

    @classmethod
    def close(cls,session_id,actual_amount):
        actual=Decimal(str(actual_amount)).quantize(Decimal("0.01"))
        with get_session() as s:
            cls._ensure(s)
            row=s.execute(text("SELECT opening_amount,status,opened_at FROM cashier_sessions WHERE id=:id"),{"id":session_id}).fetchone()
            if not row: raise ValueError("جلسة الكاشير غير موجودة")
            if row.status!="OPEN": raise ValueError("الجلسة مغلقة مسبقًا")
            sales_cash=Decimal(str(s.execute(text("""
                SELECT COALESCE(SUM(sp.amount),0) FROM sale_payments sp
                JOIN sales sl ON sl.id=sp.sale_id
                WHERE sp.payment_method='cash' AND sl.created_at>=:opened AND (sl.cashier_id=:cashier OR :cashier IS NULL)
                  AND sl.status NOT IN ('VOID','CANCELLED')
            """),{"opened":row.opened_at,"cashier":s.execute(text("SELECT cashier_id FROM cashier_sessions WHERE id=:id"),{"id":session_id}).scalar()}).scalar() or 0))
            expected=Decimal(str(row.opening_amount or 0))+sales_cash
            difference=actual-expected
            s.execute(text("""
                UPDATE cashier_sessions SET closing_amount=:a,expected_amount=:e,difference=:d,
                status='CLOSED',closed_at=CURRENT_TIMESTAMP WHERE id=:id
            """),{"a":float(actual),"e":float(expected),"d":float(difference),"id":session_id})
            AuditService.log(s,"CASHIER_SESSION_CLOSED","cashier_session",session_id)
            s.commit()
            return {"session_id":session_id,"expected":float(expected),"actual":float(actual),"difference":float(difference)}
