
import sqlite3

class POSProductSearch:
    def __init__(self, db_path="database/nizam_alqirtasiyah.db"):
        self.db_path=db_path

    def search(self, text):
        text=(text or "").strip()

        con=sqlite3.connect(self.db_path)
        con.row_factory=sqlite3.Row

        if not text:
            rows=con.execute("""
                SELECT p.id,p.sku,p.name_ar,p.sale_price,
                       COALESCE(sb.quantity,0) AS stock,
                       COALESCE(pb.barcode,'') AS barcode
                FROM products p
                LEFT JOIN stock_balances sb
                    ON sb.product_id=p.id AND sb.warehouse_id=1
                LEFT JOIN product_barcodes pb
                    ON pb.product_id=p.id AND pb.is_primary=1
                WHERE p.is_active=1
                ORDER BY p.id
                LIMIT 50
            """).fetchall()
        else:
            like=f"%{text}%"
            rows=con.execute("""
                SELECT p.id,p.sku,p.name_ar,p.sale_price,
                       COALESCE(sb.quantity,0) AS stock,
                       COALESCE(pb.barcode,'') AS barcode
                FROM products p
                LEFT JOIN stock_balances sb
                    ON sb.product_id=p.id AND sb.warehouse_id=1
                LEFT JOIN product_barcodes pb
                    ON pb.product_id=p.id AND pb.is_primary=1
                WHERE p.is_active=1
                  AND (
                       CAST(p.id AS TEXT) LIKE ?
                       OR p.sku LIKE ?
                       OR p.name_ar LIKE ?
                       OR p.name_en LIKE ?
                       OR pb.barcode LIKE ?
                  )
                ORDER BY
                    CASE WHEN p.sku=? THEN 0
                         WHEN p.name_ar=? THEN 1
                         WHEN pb.barcode=? THEN 2
                         ELSE 3 END,
                    p.id
                LIMIT 50
            """,(like,like,like,like,like,text,text,text)).fetchall()

        con.close()
        return [dict(x) for x in rows]
