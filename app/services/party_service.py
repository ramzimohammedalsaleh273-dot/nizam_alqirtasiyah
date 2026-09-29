
from sqlalchemy import text
from app.database.connection import get_session

class PartyService:

    @staticmethod
    def customers(limit=200):
        with get_session() as s:
            rows=s.execute(text("""
                SELECT
                    id,customer_code,name,phone,email,
                    tax_number,credit_limit,current_balance,is_active
                FROM customers
                ORDER BY id
                LIMIT :limit
            """),{"limit":limit}).fetchall()
            return [dict(r._mapping) for r in rows]

    @staticmethod
    def suppliers(limit=200):
        with get_session() as s:
            rows=s.execute(text("""
                SELECT
                    id,supplier_code,name,phone,email,
                    tax_number,credit_limit,current_balance,is_active
                FROM suppliers
                ORDER BY id
                LIMIT :limit
            """),{"limit":limit}).fetchall()
            return [dict(r._mapping) for r in rows]

    @staticmethod
    def customer_balance(customer_id):
        with get_session() as s:
            return float(s.execute(text("""
                SELECT COALESCE(current_balance,0)
                FROM customers
                WHERE id=:id
            """),{"id":customer_id}).scalar() or 0)
