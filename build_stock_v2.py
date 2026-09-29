import sqlite3,datetime,os,shutil

DB=r"database\nizam_alqirtasiyah.db"
os.makedirs(r"database\backups",exist_ok=True)
s=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copy2(DB,rf"database\backups\nizam_alqirtasiyah_before_stock_build_{s}.db")

c=sqlite3.connect(DB)
x=c.cursor()
now=datetime.datetime.now().isoformat(timespec="seconds")

try:
    c.execute("PRAGMA foreign_keys=ON")
    c.execute("BEGIN")

    # إنشاء جدول أرصدة المخزون
    x.execute("""
    CREATE TABLE IF NOT EXISTS stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        warehouse_id INTEGER NOT NULL,
        quantity NUMERIC NOT NULL DEFAULT 0,
        reserved_quantity NUMERIC NOT NULL DEFAULT 0,
        available_quantity NUMERIC NOT NULL DEFAULT 0,
        average_cost NUMERIC NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL,
        UNIQUE(product_id,warehouse_id),
        FOREIGN KEY(product_id) REFERENCES products(id),
        FOREIGN KEY(warehouse_id) REFERENCES warehouses(id)
    )
    """)

    warehouse=x.execute(
        "SELECT id FROM warehouses ORDER BY id LIMIT 1"
    ).fetchone()

    if not warehouse:
        raise Exception("لا يوجد مستودع")

    warehouse_id=warehouse[0]

    # إنشاء أرصدة أولية للمنتجات
    products=x.execute("""
        SELECT id,cost_price
        FROM products
        WHERE is_active=1
    """).fetchall()

    for product_id,cost in products:
        x.execute("""
        INSERT OR IGNORE INTO stock
        (product_id,warehouse_id,quantity,reserved_quantity,
         available_quantity,average_cost,updated_at)
        VALUES(?,?,?,?,?,?,?)
        """,(product_id,warehouse_id,0,0,0,cost or 0,now))

    # إضافة حركات المشتريات الموجودة
    purchase_items=x.execute("""
        SELECT pii.id,pii.product_id,pii.quantity,pii.unit_cost,
               pii.purchase_invoice_id,pii.invoice_id
        FROM purchase_invoice_items pii
    """).fetchall()

    purchase_added=0

    for iid,product_id,qty,cost,purchase_invoice_id,invoice_id in purchase_items:
        ref_id=purchase_invoice_id or invoice_id

        exists=x.execute("""
            SELECT 1 FROM stock_movements
            WHERE movement_type='purchase'
            AND reference_id=?
            AND product_id=?
        """,(ref_id,product_id)).fetchone()

        if not exists:
            x.execute("""
            INSERT INTO stock_movements
            (product_id,warehouse_id,movement_type,quantity,unit_cost,
             reference_type,reference_id,notes,created_at)
            VALUES(?,?,?,?,?,?,?,?,?)
            """,(
                product_id,warehouse_id,"purchase",qty or 0,cost or 0,
                "purchase_invoice",ref_id,
                "حركة وارد من فاتورة شراء",now
            ))
            purchase_added+=1

    # إضافة حركات المبيعات الموجودة
    sale_items=x.execute("""
        SELECT id,sale_id,product_id,quantity,unit_price
        FROM sale_items
    """).fetchall()

    sales_added=0

    for iid,sale_id,product_id,qty,price in sale_items:
        exists=x.execute("""
            SELECT 1 FROM stock_movements
            WHERE movement_type='sale'
            AND reference_id=?
            AND product_id=?
        """,(sale_id,product_id)).fetchone()

        if not exists:
            x.execute("""
            INSERT INTO stock_movements
            (product_id,warehouse_id,movement_type,quantity,unit_cost,
             reference_type,reference_id,notes,created_at)
            VALUES(?,?,?,?,?,?,?,?,?)
            """,(
                product_id,warehouse_id,"sale",-abs(qty or 0),0,
                "sale",sale_id,
                "حركة صادر من فاتورة بيع",now
            ))
            sales_added+=1

    # إعادة احتساب الرصيد من جميع الحركات
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
    updated_at=?
    """,(now,))

    # تحديث متوسط التكلفة من المنتجات
    x.execute("""
    UPDATE stock
    SET average_cost=COALESCE(
        (SELECT p.cost_price FROM products p
         WHERE p.id=stock.product_id),0)
    """)

    c.commit()

    print("="*65)
    print("تم بناء وربط المخزون بنجاح")
    print("="*65)
    print("المنتجات:",len(products))
    print("أرصدة المخزون:",x.execute(
        "SELECT COUNT(*) FROM stock").fetchone()[0])
    print("حركات المشتريات الجديدة:",purchase_added)
    print("حركات المبيعات الجديدة:",sales_added)
    print("إجمالي حركات المخزون:",x.execute(
        "SELECT COUNT(*) FROM stock_movements").fetchone()[0])
    print("إجمالي الكمية:",x.execute(
        "SELECT COALESCE(SUM(quantity),0) FROM stock").fetchone()[0])
    print("الأرصدة السالبة:",x.execute(
        "SELECT COUNT(*) FROM stock WHERE quantity<0").fetchone()[0])
    print("سلامة قاعدة البيانات:",x.execute(
        "PRAGMA integrity_check").fetchone()[0])

except Exception as e:
    c.rollback()
    print("تم التراجع عن العملية:",repr(e))
finally:
    c.close()
