import sqlite3

c=sqlite3.connect(r"database\nizam_alqirtasiyah.db")
x=c.cursor()

print("=== المبيعات ===")
for r in x.execute("""
SELECT id,invoice_number,customer_id,subtotal,tax_amount,total_amount,
       paid_amount,due_amount,status
FROM sales ORDER BY id
"""):
    print(r)

print("\n=== فواتير المشتريات ===")
for r in x.execute("""
SELECT id,invoice_number,supplier_id,subtotal,tax_amount,total_amount,
       paid_amount,due_amount,status
FROM purchase_invoices ORDER BY id
"""):
    print(r)

print("\n=== مطابقة القيود بالمصدر ===")
for r in x.execute("""
SELECT id,entry_number,description,source_type,source_id,status
FROM journal_entries
ORDER BY id
"""):
    print(r)

print("\n=== حركات العملاء ===")
for r in x.execute("""
SELECT id,customer_id,transaction_type,amount,reference_type,
       reference_id,balance_after
FROM customer_transactions
ORDER BY id
"""):
    print(r)

print("\n=== حركات الموردين ===")
for r in x.execute("""
SELECT id,supplier_id,transaction_type,amount,reference_type,
       reference_id,balance_after
FROM supplier_transactions
ORDER BY id
"""):
    print(r)

c.close()
