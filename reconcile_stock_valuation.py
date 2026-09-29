import sqlite3,datetime,os,shutil

DB=r"database\nizam_alqirtasiyah.db"
os.makedirs(r"database\backups",exist_ok=True)

stamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup=rf"database\backups\nizam_alqirtasiyah_before_stock_valuation_reconcile_{stamp}.db"
shutil.copy2(DB,backup)

c=sqlite3.connect(DB)
x=c.cursor()

try:
    c.execute("PRAGMA foreign_keys=ON")
    c.execute("BEGIN")

    rows=x.execute("""
    SELECT product_id,warehouse_id
    FROM stock
    """).fetchall()

    for product_id,warehouse_id in rows:

        # الكمية الفعلية
        qty=x.execute("""
        SELECT COALESCE(SUM(quantity),0)
        FROM stock_movements
        WHERE product_id=? AND warehouse_id=?
        """,(product_id,warehouse_id)).fetchone()[0]

        # قيمة المخزون = إجمالي الوارد - إجمالي تكلفة الصادر
        incoming=x.execute("""
        SELECT COALESCE(SUM(quantity*unit_cost),0)
        FROM stock_movements
        WHERE product_id=? AND warehouse_id=? AND quantity>0
        """,(product_id,warehouse_id)).fetchone()[0]

        outgoing=x.execute("""
        SELECT COALESCE(SUM(ABS(quantity)*unit_cost),0)
        FROM stock_movements
        WHERE product_id=? AND warehouse_id=? AND quantity<0
        """,(product_id,warehouse_id)).fetchone()[0]

        value=float(incoming)-float(outgoing)
        avg=value/float(qty) if float(qty)!=0 else 0

        x.execute("""
        UPDATE stock
        SET quantity=?,
            available_quantity=?,
            reserved_quantity=0,
            average_cost=?,
            updated_at=CURRENT_TIMESTAMP
        WHERE product_id=? AND warehouse_id=?
        """,(qty,qty,avg,product_id,warehouse_id))

    c.commit()

    stock=x.execute("""
    SELECT
        COALESCE(SUM(quantity),0),
        COALESCE(SUM(quantity*average_cost),0)
    FROM stock
    """).fetchone()

    gl=x.execute("""
    SELECT
        COALESCE(SUM(j.debit),0)-
        COALESCE(SUM(j.credit),0)
    FROM journal_entry_lines j
    JOIN accounts a ON a.id=j.account_id
    WHERE a.account_code='1400'
    """).fetchone()[0]

    debit=x.execute("""
    SELECT COALESCE(SUM(debit),0)
    FROM journal_entry_lines
    """).fetchone()[0]

    credit=x.execute("""
    SELECT COALESCE(SUM(credit),0)
    FROM journal_entry_lines
    """).fetchone()[0]

    print("="*65)
    print("تمت مطابقة تقييم المخزون مع المحاسبة")
    print("="*65)
    print("النسخة الاحتياطية:",backup)
    print("كمية المخزون:",stock[0])
    print("قيمة المخزون:",round(stock[1],2))
    print("رصيد حساب 1400:",round(gl,2))
    print("الفرق:",round(float(stock[1])-float(gl),2))
    print("إجمالي المدين:",round(debit,2))
    print("إجمالي الدائن:",round(credit,2))
    print("فرق القيود:",round(debit-credit,2))
    print("سلامة SQLite:",x.execute("PRAGMA integrity_check").fetchone()[0])
    print("أخطاء العلاقات:",len(x.execute("PRAGMA foreign_key_check").fetchall()))

except Exception as e:
    c.rollback()
    print("حدث خطأ وتم التراجع بالكامل:",repr(e))
finally:
    c.close()
