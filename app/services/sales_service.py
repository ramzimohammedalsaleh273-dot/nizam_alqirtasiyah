from sqlalchemy import text
from app.database.connection import get_session


class SalesService:

    @staticmethod
    def list_sales(limit=100):
        with get_session() as s:
            rows=s.execute(text("""
                SELECT
                    id,
                    invoice_number,
                    customer_id,
                    subtotal,
                    discount_amount,
                    tax_amount,
                    total_amount,
                    paid_amount,
                    due_amount,
                    status,
                    created_at
                FROM sales
                ORDER BY id DESC
                LIMIT :limit
            """), {"limit":limit}).fetchall()

            return [dict(r._mapping) for r in rows]


    @staticmethod
    def get_sale(sale_id):
        with get_session() as s:
            sale=s.execute(text("""
                SELECT *
                FROM sales
                WHERE id=:id
            """), {"id":sale_id}).fetchone()

            if not sale:
                return None

            items=s.execute(text("""
                SELECT
                    si.*,
                    p.name_ar,
                    p.sku
                FROM sale_items si
                JOIN products p
                    ON p.id=si.product_id
                WHERE si.sale_id=:id
                ORDER BY si.id
            """), {"id":sale_id}).fetchall()

            result=dict(sale._mapping)
            result["items"]=[dict(x._mapping) for x in items]

            return result


class PurchaseService:

    @staticmethod
    def list_purchases(limit=100):
        with get_session() as s:
            rows=s.execute(text("""
                SELECT
                    pi.id,
                    pi.invoice_number,
                    pi.supplier_id,
                    pi.subtotal,
                    pi.tax_amount,
                    pi.total_amount,
                    pi.paid_amount,
                    pi.due_amount,
                    pi.status,
                    pi.invoice_date AS purchase_date
                FROM purchase_invoices pi
                ORDER BY pi.id DESC
                LIMIT :limit
            """), {"limit":limit}).fetchall()

            return [dict(r._mapping) for r in rows]


    @staticmethod
    def get_purchase(invoice_id):
        with get_session() as s:
            invoice=s.execute(text("""
                SELECT *
                FROM purchase_invoices
                WHERE id=:id
            """), {"id":invoice_id}).fetchone()

            if not invoice:
                return None

            item_columns=[
                row[1]
                for row in s.connection().exec_driver_sql(
                    "PRAGMA table_info(purchase_invoice_items)"
                ).fetchall()
            ]

            # تحديد اسم عمود ربط الفاتورة الحقيقي
            if "invoice_id" in item_columns:
                invoice_fk="invoice_id"
            elif "purchase_invoice_id" in item_columns:
                invoice_fk="purchase_invoice_id"
            else:
                invoice_fk=None

            if invoice_fk:
                items=s.execute(text(f"""
                    SELECT
                        pii.*,
                        p.name_ar,
                        p.sku
                    FROM purchase_invoice_items pii
                    JOIN products p
                        ON p.id=pii.product_id
                    WHERE pii.{invoice_fk}=:id
                    ORDER BY pii.id
                """.replace("{invoice_fk}",invoice_fk)), {"id":invoice_id}).fetchall()
            else:
                items=[]

            result=dict(invoice._mapping)
            result["items"]=[dict(x._mapping) for x in items]

            return result


    @staticmethod
    def supplier_balance(supplier_id):
        with get_session() as s:
            return float(
                s.execute(text("""
                    SELECT COALESCE(current_balance,0)
                    FROM suppliers
                    WHERE id=:id
                """), {"id":supplier_id}).scalar() or 0
            )
