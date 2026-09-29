from sqlalchemy import text
from app.database.connection import get_session


class PurchaseService:
    """خدمات قراءة المشتريات، مستقلة عن خدمات المبيعات."""

    @staticmethod
    def list_purchases(limit=100):
        with get_session() as s:
            rows = s.execute(text("""
                SELECT
                    pi.id, pi.invoice_number, pi.supplier_id,
                    pi.subtotal, pi.tax_amount, pi.total_amount,
                    pi.paid_amount, pi.due_amount, pi.status,
                    pi.invoice_date AS purchase_date
                FROM purchase_invoices pi
                ORDER BY pi.id DESC
                LIMIT :limit
            """), {"limit": limit}).fetchall()
            return [dict(r._mapping) for r in rows]

    @staticmethod
    def get_purchase(invoice_id):
        with get_session() as s:
            invoice = s.execute(text("""
                SELECT *
                FROM purchase_invoices
                WHERE id=:id
            """), {"id": invoice_id}).fetchone()
            if not invoice:
                return None

            columns = {
                row[1]
                for row in s.connection().exec_driver_sql(
                    "PRAGMA table_info(purchase_invoice_items)"
                ).fetchall()
            }
            if "invoice_id" in columns:
                invoice_fk = "invoice_id"
            elif "purchase_invoice_id" in columns:
                invoice_fk = "purchase_invoice_id"
            else:
                invoice_fk = None

            items = []
            if invoice_fk:
                rows = s.execute(text(f"""
                    SELECT pii.*, p.name_ar, p.sku
                    FROM purchase_invoice_items pii
                    JOIN products p ON p.id=pii.product_id
                    WHERE pii.{invoice_fk}=:id
                    ORDER BY pii.id
                """), {"id": invoice_id}).fetchall()
                items = [dict(x._mapping) for x in rows]

            result = dict(invoice._mapping)
            result["items"] = items
            return result

    @staticmethod
    def supplier_balance(supplier_id):
        with get_session() as s:
            return float(
                s.execute(text("""
                    SELECT COALESCE(current_balance,0)
                    FROM suppliers
                    WHERE id=:id
                """), {"id": supplier_id}).scalar() or 0
            )
