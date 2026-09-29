import sqlite3,datetime,os,shutil

DB=r"database\nizam_alqirtasiyah.db"
os.makedirs(r"database\backups",exist_ok=True)
s=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copy2(DB,rf"database\backups\nizam_alqirtasiyah_before_party_balances_{s}.db")

c=sqlite3.connect(DB)
x=c.cursor()

try:
    c.execute("BEGIN")

    # أرصدة العملاء:
    # المبيعات الآجلة - المدفوعات
    customers=x.execute("SELECT id,opening_balance FROM customers").fetchall()

    for cid,opening in customers:
        sales_due=x.execute("""
            SELECT COALESCE(SUM(due_amount),0)
            FROM sales
            WHERE customer_id=?
        """,(cid,)).fetchone()[0] or 0

        payments=x.execute("""
            SELECT COALESCE(SUM(amount),0)
            FROM customer_payments
            WHERE customer_id=?
        """,(cid,)).fetchone()[0] or 0

        balance=(opening or 0)+sales_due-payments

        x.execute("""
            UPDATE customers
            SET current_balance=?,updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        """,(balance,cid))

    # أرصدة الموردين:
    # المستحق من فواتير الشراء - المدفوع
    suppliers=x.execute("SELECT id FROM suppliers").fetchall()

    for sid, in suppliers:
        purchases_due=x.execute("""
            SELECT COALESCE(SUM(due_amount),0)
            FROM purchase_invoices
            WHERE supplier_id=?
        """,(sid,)).fetchone()[0] or 0

        supplier_paid=x.execute("""
            SELECT COALESCE(SUM(amount),0)
            FROM supplier_transactions
            WHERE supplier_id=?
              AND transaction_type IN ('payment','settlement')
        """,(sid,)).fetchone()[0] or 0

        balance=purchases_due-supplier_paid

        x.execute("""
            UPDATE suppliers
            SET current_balance=?
            WHERE id=?
        """,(balance,sid))

    c.commit()

    print("="*65)
    print("تم تحديث أرصدة العملاء والموردين")
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
