import sqlite3,datetime,os,shutil

DB=r"database\nizam_alqirtasiyah.db"
os.makedirs(r"database\backups",exist_ok=True)
s=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copy2(DB,rf"database\backups\nizam_alqirtasiyah_before_supplier_transactions_{s}.db")

c=sqlite3.connect(DB)
x=c.cursor()
now=datetime.datetime.now().isoformat(timespec="seconds")

try:
    c.execute("PRAGMA foreign_keys=ON")
    c.execute("BEGIN")

    x.execute("""
    CREATE TABLE IF NOT EXISTS supplier_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        supplier_id INTEGER NOT NULL,
        transaction_type VARCHAR(50) NOT NULL,
        amount NUMERIC NOT NULL DEFAULT 0,
        reference_type VARCHAR(50),
        reference_id INTEGER,
        balance_after NUMERIC NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
    )
    """)

    rows=x.execute("""
        SELECT id,supplier_id,total_amount,paid_amount,due_amount
        FROM purchase_invoices
        WHERE supplier_id IS NOT NULL
    """).fetchall()

    added=0

    for pid,supplier_id,total,paid,due in rows:
        exists=x.execute("""
            SELECT 1 FROM supplier_transactions
            WHERE reference_type='purchase_invoice' AND reference_id=?
        """,(pid,)).fetchone()

        if not exists:
            x.execute("""
            INSERT INTO supplier_transactions
            (supplier_id,transaction_type,amount,reference_type,
             reference_id,balance_after,created_at)
            VALUES(?,?,?,?,?,?,?)
            """,(
                supplier_id,
                "purchase",
                total or 0,
                "purchase_invoice",
                pid,
                due or 0,
                now
            ))
            added+=1

    c.commit()

    print("="*65)
    print("تم إنشاء وربط حركات الموردين بنجاح")
    print("="*65)
    print("supplier_transactions:",x.execute(
        "SELECT COUNT(*) FROM supplier_transactions").fetchone()[0])
    print("الحركات الجديدة:",added)
    print("الموردون:",x.execute(
        "SELECT COUNT(*) FROM suppliers").fetchone()[0])
    print("فواتير الشراء:",x.execute(
        "SELECT COUNT(*) FROM purchase_invoices").fetchone()[0])
    print("سلامة قاعدة البيانات:",x.execute(
        "PRAGMA integrity_check").fetchone()[0])

except Exception as e:
    c.rollback()
    print("تم التراجع عن العملية:",repr(e))
finally:
    c.close()
