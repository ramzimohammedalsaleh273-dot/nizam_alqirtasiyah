
from sqlalchemy import text
from app.database.connection import get_session

class InventoryService:

    @staticmethod
    def search_products(term="", warehouse_id=1):
        with get_session() as s:
            q = """
            SELECT
                p.id,p.sku,p.name_ar,p.cost_price,p.sale_price,
                p.wholesale_price,p.school_price,p.corporate_price,
                COALESCE(st.quantity,0) AS quantity,
                COALESCE(st.available_quantity,0) AS available_quantity
            FROM products p
            LEFT JOIN stock st ON st.product_id=p.id AND st.warehouse_id=:warehouse_id
            WHERE p.is_active=1
            """
            params={"warehouse_id": warehouse_id}
            if term:
                q += """
                AND (
                    p.name_ar LIKE :term
                    OR p.name_en LIKE :term
                    OR p.sku LIKE :term
                    OR EXISTS(
                        SELECT 1 FROM product_barcodes pb
                        WHERE pb.product_id=p.id
                        AND pb.barcode LIKE :term
                    )
                )
                """
                params["term"]=f"%{term}%"

            q += " ORDER BY p.id LIMIT 100"

            return [dict(r._mapping) for r in s.execute(
                text(q),params
            ).fetchall()]

    @staticmethod
    def get_product(product_id, warehouse_id=1):
        with get_session() as s:
            r=s.execute(text("""
                SELECT
                    p.*,
                    COALESCE(st.quantity,0) quantity,
                    COALESCE(st.available_quantity,0) available_quantity,
                    COALESCE(st.average_cost,0) average_cost
                FROM products p
                LEFT JOIN stock st ON st.product_id=p.id AND st.warehouse_id=:warehouse_id
                WHERE p.id=:id
            """),{"id":product_id,"warehouse_id":warehouse_id}).fetchone()

            return dict(r._mapping) if r else None

    @staticmethod
    def available_quantity(product_id,warehouse_id=1):
        with get_session() as s:
            return float(s.execute(text("""
                SELECT COALESCE(available_quantity,0)
                FROM stock
                WHERE product_id=:p AND warehouse_id=:w
            """),{"p":product_id,"w":warehouse_id}).scalar() or 0)

    @staticmethod
    def low_stock(limit=100):
        with get_session() as s:
            rows=s.execute(text("""
                SELECT p.id,p.sku,p.name_ar,p.reorder_point,p.min_stock,
                       COALESCE(st.available_quantity,0) AS available_quantity
                FROM products p
                LEFT JOIN stock st ON st.product_id=p.id
                WHERE p.is_active=1
                  AND COALESCE(st.available_quantity,0) <= COALESCE(NULLIF(p.reorder_point,0),p.min_stock,0)
                ORDER BY available_quantity ASC,p.id
                LIMIT :limit
            """),{"limit":limit}).fetchall()
            return [dict(r._mapping) for r in rows]
