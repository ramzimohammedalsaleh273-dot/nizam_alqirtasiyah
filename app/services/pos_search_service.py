import sqlite3


class POSProductSearch:
    """بحث نقطة البيع من مخزون التشغيل الفعلي مع ترتيب ذكي للنتائج."""

    def __init__(self, db_path="database/nizam_alqirtasiyah.db", warehouse_id=1):
        self.db_path = db_path
        self.warehouse_id = int(warehouse_id)

    def search(self, text):
        text = (text or "").strip()
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        try:
            like = f"%{text}%"
            rows = con.execute(
                """
                SELECT
                    p.id,
                    p.sku,
                    p.name_ar,
                    p.name_en,
                    p.sale_price,
                    COALESCE(st.quantity,0) AS stock,
                    COALESCE(st.quantity-st.reserved_quantity,0) AS available_quantity,
                    COALESCE(pb.barcode,'') AS barcode
                FROM products p
                LEFT JOIN stock_balances st
                    ON st.product_id=p.id AND st.warehouse_id=?
                LEFT JOIN product_barcodes pb
                    ON pb.product_id=p.id AND pb.is_primary=1
                WHERE p.is_active=1
                  AND (
                    ?=''
                    OR CAST(p.id AS TEXT)=?
                    OR p.sku=?
                    OR pb.barcode=?
                    OR p.name_ar LIKE ?
                    OR p.name_en LIKE ?
                    OR p.sku LIKE ?
                    OR pb.barcode LIKE ?
                  )
                ORDER BY
                    CASE
                        WHEN ?<>'' AND pb.barcode=? THEN 0
                        WHEN ?<>'' AND p.sku=? THEN 1
                        WHEN ?<>'' AND CAST(p.id AS TEXT)=? THEN 2
                        WHEN ?<>'' AND p.name_ar=? THEN 3
                        ELSE 4
                    END,
                    p.id
                LIMIT 50
                """,
                (
                    self.warehouse_id,
                    text, text, text, text,
                    like, like, like, like,
                    text, text, text, text, text, text, text, text,
                ),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            con.close()
