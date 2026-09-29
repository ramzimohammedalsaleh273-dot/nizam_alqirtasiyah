import sqlite3
c=sqlite3.connect(r"database\nizam_alqirtasiyah.db")
for t in ["sales","purchase_invoices","customer_transactions","customer_payments","supplier_transactions"]:
 print("\n===",t,"===")
 try:
  print(" | ".join(r[1] for r in c.execute(f'PRAGMA table_info("{t}")')))
 except: pass
c.close()
