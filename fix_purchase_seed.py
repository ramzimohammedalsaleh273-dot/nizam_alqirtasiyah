import sqlite3,datetime,os,shutil

DB=r"database\nizam_alqirtasiyah.db"
os.makedirs(r"database\backups",exist_ok=True)
s=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copy2(DB,rf"database\backups\nizam_alqirtasiyah_before_purchase_seed_fix_{s}.db")

c=sqlite3.connect(DB)
x=c.cursor()
now=datetime.datetime.now().isoformat(timespec="seconds")

try:
    c.execute("BEGIN")

    # تصحيح إجمالي فواتير seed المدفوعة
    rows=x.execute("""
        SELECT id,subtotal,paid_amount
        FROM purchase_invoices
        WHERE id IN (4,5,6)
    """).fetchall()

    for pid,subtotal,paid in rows:
        total=paid or subtotal or 0

        x.execute("""
        UPDATE purchase_invoices
        SET total_amount=?,
            due_amount=0,
            paid_amount=?,
            status='paid'
        WHERE id=?
        """,(total,total,pid))

        # تصحيح حركة المورد المرتبطة
        x.execute("""
        UPDATE supplier_transactions
        SET amount=?,
            balance_after=0
        WHERE reference_type='purchase_invoice'
          AND reference_id=?
        """,(total,pid))

    c.commit()

    print("="*65)
    print("تم تصحيح فواتير الشراء التجريبية")
    print("="*65)

    for r in x.execute("""
        SELECT id,invoice_number,subtotal,total_amount,
               paid_amount,due_amount,status
        FROM purchase_invoices
        WHERE id IN (4,5,6)
        ORDER BY id
    """):
        print(r)

    print("\nحركات الموردين:")
    for r in x.execute("""
        SELECT reference_id,amount,balance_after
        FROM supplier_transactions
        WHERE reference_id IN (4,5,6)
        ORDER BY reference_id
    """):
        print(r)

    print("\nسلامة قاعدة البيانات:",
          x.execute("PRAGMA integrity_check").fetchone()[0])

except Exception as e:
    c.rollback()
    print("تم التراجع عن العملية:",repr(e))
finally:
    c.close()
