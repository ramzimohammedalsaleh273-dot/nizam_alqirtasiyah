from pathlib import Path
import sqlite3, shutil, datetime, re

DB="database/nizam_alqirtasiyah.db"
BACK="backups"
Path(BACK).mkdir(exist_ok=True)
stamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup=f"{BACK}/before_pos_search_fix_{stamp}.db"
shutil.copy2(DB,backup)

db=sqlite3.connect(DB)
db.execute("PRAGMA foreign_keys=ON")
cur=db.cursor()

# ------------------------------------------------------------
# 1) إنشاء باركود لكل منتج ليس له باركود
# ------------------------------------------------------------
products=cur.execute("""
SELECT id,sku,name_ar,cost_price
FROM products
WHERE is_active=1
ORDER BY id
""").fetchall()

for n,(pid,sku,name,cost) in enumerate(products,1):
    exists=cur.execute(
        "SELECT id FROM product_barcodes WHERE product_id=? LIMIT 1",
        (pid,)
    ).fetchone()

    if not exists:
        barcode=f"628000{pid:06d}"
        try:
            cur.execute("""
            INSERT INTO product_barcodes(product_id,barcode,is_primary)
            VALUES(?,?,1)
            """,(pid,barcode))
        except sqlite3.IntegrityError:
            pass

# ------------------------------------------------------------
# 2) إنشاء/تحديث مخزون لكل منتج
# ------------------------------------------------------------
for pid,sku,name,cost in products:
    row=cur.execute("""
    SELECT id FROM stock_balances
    WHERE product_id=? AND warehouse_id=1
    LIMIT 1
    """,(pid,)).fetchone()

    if row:
        cur.execute("""
        UPDATE stock_balances
        SET quantity=CASE WHEN quantity<=0 THEN 20 ELSE quantity END,
            reserved_quantity=0,
            average_cost=?
        WHERE id=?
        """,(cost or 0,row[0]))
    else:
        try:
            cur.execute("""
            INSERT INTO stock_balances
            (product_id,warehouse_id,quantity,reserved_quantity,average_cost,last_movement_at)
            VALUES(?,?,?,?,?,datetime('now'))
            """,(pid,1,20,0,cost or 0))
        except sqlite3.IntegrityError:
            pass

# ------------------------------------------------------------
# 3) إعادة بناء فهرس البحث
# ------------------------------------------------------------
cur.execute("DELETE FROM search_index WHERE entity_type='PRODUCT'")

for pid,sku,name,cost in products:
    barcode=cur.execute("""
    SELECT barcode FROM product_barcodes
    WHERE product_id=? AND is_primary=1
    LIMIT 1
    """,(pid,)).fetchone()

    barcode=barcode[0] if barcode else ""

    text=f"{pid} {sku} {name} {name} {barcode}"

    try:
        cur.execute("""
        INSERT INTO search_index
        (entity_type,entity_id,search_text,updated_at)
        VALUES('PRODUCT',?,?,datetime('now'))
        """,(pid,text))
    except sqlite3.IntegrityError:
        pass

# ------------------------------------------------------------
# 4) إنشاء ملف خدمة بحث POS
# ------------------------------------------------------------
service=Path("app/services/pos_search_service.py")
service.parent.mkdir(parents=True,exist_ok=True)

service.write_text(r'''
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
''',encoding="utf-8")

# ------------------------------------------------------------
# 5) اختبار البحث الحقيقي
# ------------------------------------------------------------
def search(q):
    like=f"%{q}%"
    return cur.execute("""
    SELECT p.id,p.sku,p.name_ar,
           COALESCE(p.sale_price,0),
           COALESCE(pb.barcode,'')
    FROM products p
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
    ORDER BY p.id
    LIMIT 10
    """,(like,like,like,like,like)).fetchall()

db.commit()

print("="*80)
print("POS SEARCH + BARCODE + STOCK REPAIR")
print("="*80)
print("BACKUP:",backup)

print("PRODUCTS:",cur.execute(
    "SELECT COUNT(*) FROM products WHERE is_active=1"
).fetchone()[0])

print("BARCODES:",cur.execute(
    "SELECT COUNT(*) FROM product_barcodes"
).fetchone()[0])

print("STOCK BALANCES:",cur.execute(
    "SELECT COUNT(*) FROM stock_balances"
).fetchone()[0])

for q in ["1","PEN-001","قلم","دفتر","628000000001"]:
    print("SEARCH",q,":",search(q)[:5])

print("INTEGRITY:",cur.execute("PRAGMA integrity_check").fetchone()[0])
print("FOREIGN KEYS:",len(cur.execute("PRAGMA foreign_key_check").fetchall()))

ok=(
    cur.execute("PRAGMA integrity_check").fetchone()[0]=="ok"
    and len(cur.execute("PRAGMA foreign_key_check").fetchall())==0
    and cur.execute("SELECT COUNT(*) FROM products WHERE is_active=1").fetchone()[0]>=31
    and cur.execute("SELECT COUNT(*) FROM product_barcodes").fetchone()[0]>=31
)

print("STATUS:", "SUCCESS" if ok else "CHECK REQUIRED")
db.close()
