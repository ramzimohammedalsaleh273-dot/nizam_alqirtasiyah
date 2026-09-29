import sqlite3,datetime,os,shutil
DB=r"database\nizam_alqirtasiyah.db"
os.makedirs(r"database\backups",exist_ok=True)
s=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copy2(DB,rf"database\backups\nizam_alqirtasiyah_before_customer_links_{s}.db")
c=sqlite3.connect(DB); x=c.cursor(); now=datetime.datetime.now().isoformat(timespec="seconds")

try:
 c.execute("BEGIN")

 # حركات العملاء
 for sid,cid,amount in x.execute("SELECT id,customer_id,total_amount FROM sales WHERE customer_id IS NOT NULL").fetchall():
  x.execute("""INSERT OR IGNORE INTO customer_transactions
  (customer_id,transaction_type,amount,reference_type,reference_id,balance_after,created_at)
  VALUES(?,?,?,?,?,?,?)""",(cid,"sale",amount,"sale",sid,0,now))

 # مدفوعات العملاء
 for sid,cid,amount,paid in x.execute("SELECT id,customer_id,total_amount,paid_amount FROM sales WHERE customer_id IS NOT NULL").fetchall():
  if paid and paid>0:
   x.execute("""INSERT OR IGNORE INTO customer_payments
   (customer_id,amount,payment_method,reference_number,notes,created_at)
   VALUES(?,?,?,?,?,?)""",(cid,paid,"cash",f"SALE-{sid}","دفعة مرتبطة بفاتورة بيع",now))

 c.commit()

 print("="*65)
 print("تم ربط العملاء بالعمليات بنجاح")
 print("="*65)
 print("customer_transactions:",x.execute("SELECT COUNT(*) FROM customer_transactions").fetchone()[0])
 print("customer_payments:",x.execute("SELECT COUNT(*) FROM customer_payments").fetchone()[0])
 print("sales:",x.execute("SELECT COUNT(*) FROM sales").fetchone()[0])
 print("purchase_invoices:",x.execute("SELECT COUNT(*) FROM purchase_invoices").fetchone()[0])
 print("سلامة قاعدة البيانات:",x.execute("PRAGMA integrity_check").fetchone()[0])

except Exception as e:
 c.rollback()
 print("تم التراجع:",repr(e))
finally:
 c.close()
