from sqlalchemy import text
from app.database.connection import get_session


class SalesService:

    @staticmethod
    def list_sales(limit=100):
        with get_session() as s:
            rows = s.execute(text("""
                SELECT
                    id, invoice_number, customer_id, subtotal,
                    discount_amount, tax_amount, total_amount,
                    paid_amount, due_amount, status, created_at
                FROM sales
                ORDER BY id DESC
                LIMIT :limit
            """), {"limit": limit}).fetchall()
            return [dict(r._mapping) for r in rows]

    @staticmethod
    def get_sale(sale_id):
        with get_session() as s:
            sale = s.execute(text("""
                SELECT *
                FROM sales
                WHERE id=:id
            """), {"id": sale_id}).fetchone()
            if not sale:
                return None
            items = s.execute(text("""
                SELECT si.*, p.name_ar, p.sku
                FROM sale_items si
                JOIN products p ON p.id=si.product_id
                WHERE si.sale_id=:id
                ORDER BY si.id
            """), {"id": sale_id}).fetchall()
            result = dict(sale._mapping)
            result["items"] = [dict(x._mapping) for x in items]
            return result
