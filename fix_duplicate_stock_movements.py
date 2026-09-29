import sqlite3,datetime,os,shutil

DB=r"database\nizam_alqirtasiyah.db"
os.makedirs(r"database\backups",exist_ok=True)
s=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copy2(DB,rf"database\backups\nizam_alqirtasiyah_before_stock_duplicate_fix_{s}.db")

c=sqlite3.connect(DB)
x=c.cursor()

try:
    c.execute("PRAGMA foreign_keys=ON")
    c.execute("BEGIN")

    # هذه الحركات أضيفت لاحقاً من الفواتير، لكنها تكرر
    # الحركات الأصلية الموجودة مسبقاً لنفس المبيعات والمشتريات.
    purchase_ids=(9,10,11)
    sale_ids=(12,13,14,15)

    before=x.execute(
        "SELECT COUNT(*) FROM stock_movements"
    ).fetchone()[0]

    x.execute("""
        DELETE FROM stock_movements
        WHERE id IN (9,10,11,12,13,14,15)
    """)

    deleted=before-x.execute(
        "SELECT COUNT(*) FROM stock_movements"
    ).fetchone()[0]

    # إعادة إنشاء أرصدة المخزون من الحركات المتبقية
    x.execute("""
    UPDATE stock
    SET quantity=(
        SELECT COALESCE(SUM(sm.quantity),0)
        FROM stock_movements sm
        WHERE sm.product_id=stock.product_id
          AND sm.warehouse_id=stock.warehouse_id
    ),
    available_quantity=(
        SELECT COALESCE(SUM(sm.quantity),0)
        FROM stock_movements sm
        WHERE sm.product_id=stock.product_id
          AND sm.warehouse_id=stock.warehouse_id
    ),
    updated_at=CURRENT_TIMESTAMP
    """)

    # إعادة حساب متوسط التكلفة من الحركات الواردة المتبقية
    x.execute("""
    UPDATE stock
    SET average_cost=COALESCE((
        SELECT
            CASE
                WHEN SUM(CASE WHEN sm.quantity>0 THEN sm.quantity ELSE 0 END)>0
                THEN
                    SUM(CASE WHEN sm.quantity>0
                             THEN sm.quantity*sm.unit_cost ELSE 0 END)
                    /
                    SUM(CASE WHEN sm.quantity>0
                             THEN sm.quantity ELSE 0 END)
                ELSE 0
            END
        FROM stock_movements sm
        WHERE sm.product_id=stock.product_id
          AND sm.warehouse_id=stock.warehouse_id
    ),0)
    """)

    c.commit()

    print("="*65)
    print("تم تنظيف حركات المخزون المكررة")
    print("="*65)
    print("الحركات قبل التنظيف:",before)
    print("الحركات المحذوفة:",deleted)
    print("الحركات بعد التنظيف:",x.execute(
        "SELECT COUNT(*) FROM stock_movements").fetchone()[0])

    r=x.execute("""
    SELECT COUNT(*),
           COALESCE(SUM(quantity),0),
           COALESCE(SUM(quantity*average_cost),0)
    FROM stock
    """).fetchone()

    print("أصناف المخزون:",r[0])
    print("إجمالي الكمية:",r[1])
    print("قيمة المخزون:",r[2])
    print("الأرصدة السالبة:",x.execute(
        "SELECT COUNT(*) FROM stock WHERE quantity<0").fetchone()[0])

    print("سلامة SQLite:",x.execute(
        "PRAGMA integrity_check").fetchone()[0])

    print("أخطاء العلاقات:",len(x.execute(
        "PRAGMA foreign_key_check").fetchall()))

except Exception as e:
    c.rollback()
    print("تم التراجع عن العملية:",repr(e))
finally:
    c.close()
