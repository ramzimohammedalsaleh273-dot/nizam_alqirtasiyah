from sqlalchemy import text
from app.database.connection import get_session


class SalesService:

    @staticmethod
    def list_sales(limit=100):
        with get_session() as s:
            rows = s.execute(text("""
                SELECT
                    s.id, s.invoice_number, s.customer_id, COALESCE(c.name,'نقدي') AS customer_name,
                    COALESCE(u.username,'—') AS cashier_name, s.subtotal,
                    s.discount_amount, s.tax_amount, s.total_amount,
                    s.paid_amount, s.due_amount, s.status, s.created_at
                FROM sales s
                LEFT JOIN customers c ON c.id=s.customer_id
                LEFT JOIN users u ON u.id=s.cashier_id
                ORDER BY s.id DESC
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
