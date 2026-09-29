import sqlite3,datetime,os,shutil

DB=r"database\nizam_alqirtasiyah.db"
os.makedirs(r"database\backups",exist_ok=True)
s=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copy2(DB,rf"database\backups\nizam_alqirtasiyah_before_balance_fix_{s}.db")

c=sqlite3.connect(DB)
x=c.cursor()

try:
    c.execute("BEGIN")

    # رصيد العميل = الرصيد الافتتاحي + إجمالي المستحق غير المدفوع
    for cid,opening in x.execute(
        "SELECT id,opening_balance FROM customers"
    ).fetchall():

        due=x.execute("""
            SELECT COALESCE(SUM(due_amount),0)
            FROM sales
            WHERE customer_id=?
        """,(cid,)).fetchone()[0] or 0

        balance=(opening or 0)+due

        x.execute("""
            UPDATE customers
            SET current_balance=?,updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        """,(balance,cid))

    # المورد: الرصيد = إجمالي المستحق من فواتير الشراء
    for sid, in x.execute("SELECT id FROM suppliers").fetchall():

        due=x.execute("""
            SELECT COALESCE(SUM(due_amount),0)
            FROM purchase_invoices
            WHERE supplier_id=?
        """,(sid,)).fetchone()[0] or 0

        x.execute("""
            UPDATE suppliers
            SET current_balance=?
            WHERE id=?
        """,(due,sid))

    c.commit()

    print("="*65)
    print("تم تصحيح أرصدة العملاء والموردين")
    print("="*65)

    print("العملاء:")
    for r in x.execute("""
        SELECT id,name,current_balance
        FROM customers
        WHERE current_balance<>0
        ORDER BY id
    """):
        print(r)

    print("\nالموردون:")
    for r in x.execute("""
        SELECT id,name,current_balance
        FROM suppliers
        WHERE current_balance<>0
        ORDER BY id
    """):
        print(r)

    print("\nإجمالي رصيد العملاء:",
          x.execute("SELECT COALESCE(SUM(current_balance),0) FROM customers").fetchone()[0])

    print("إجمالي رصيد الموردين:",
          x.execute("SELECT COALESCE(SUM(current_balance),0) FROM suppliers").fetchone()[0])

    print("سلامة قاعدة البيانات:",
          x.execute("PRAGMA integrity_check").fetchone()[0])

except Exception as e:
    c.rollback()
    print("تم التراجع عن العملية:",repr(e))
finally:
    c.close()
