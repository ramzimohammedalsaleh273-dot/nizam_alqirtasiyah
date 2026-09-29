import sqlite3

c=sqlite3.connect(r"database\nizam_alqirtasiyah.db")
x=c.cursor()

print("=== تفاصيل فواتير الشراء 4-6 ===")
for r in x.execute("""
SELECT id,invoice_number,supplier_id,subtotal,tax_amount,
       total_amount,paid_amount,due_amount,status
FROM purchase_invoices
WHERE id>=4
ORDER BY id
"""):
    print(r)

print("\n=== بنود فواتير الشراء 4-6 ===")
for r in x.execute("""
SELECT id,invoice_id,purchase_invoice_id,product_id,
       quantity,unit_cost,tax_amount,line_total
FROM purchase_invoice_items
WHERE invoice_id>=4 OR purchase_invoice_id>=4
ORDER BY id
"""):
    print(r)

print("\n=== مدفوعات المشتريات إن وجدت ===")
for t in ["supplier_payments","purchase_payments"]:
    try:
        print("\n",t)
        for r in x.execute(f'SELECT * FROM "{t}"'):
            print(r)
    except:
        print("الجدول غير موجود")

c.close()
