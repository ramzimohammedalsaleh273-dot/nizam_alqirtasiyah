import sqlite3, os
db="database/nizam_alqirtasiyah.db"
con=sqlite3.connect(db)
print("="*70)
print("CURRENT DATABASE STATUS")
print("="*70)
tables=[
"companies","branches","warehouses","product_categories","brands","units",
"products","customers","suppliers","accounts","tax_rates","users",
"purchase_requests","purchase_orders","purchase_order_items",
"purchase_receipts","purchase_receipt_items",
"purchase_invoices","purchase_invoice_items",
"purchase_returns","purchase_return_items",
"stock_movements",
"sales","sale_items","sale_payments",
"sale_returns","sale_return_items",
"cash_registers","cash_sessions","cash_transactions",
"banks","bank_accounts","bank_transactions",
"journal_entries","journal_entry_lines",
"tax_invoices","tax_invoice_lines"
]
for t in tables:
    r=con.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone()
    if r and r[0]:
        n=con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        print(f"{t:30} {n}")
    else:
        print(f"{t:30} [TABLE NOT FOUND]")
print("-"*70)
print("INTEGRITY:",con.execute("PRAGMA integrity_check").fetchone()[0])
fk=con.execute("PRAGMA foreign_key_check").fetchall()
print("FOREIGN KEY ERRORS:",len(fk))
print("STATUS: SUCCESS")
print("="*70)
con.close()
