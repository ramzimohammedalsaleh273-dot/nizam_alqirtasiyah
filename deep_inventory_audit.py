import sqlite3

c=sqlite3.connect(r"database\nizam_alqirtasiyah.db")
x=c.cursor()

print("=== جميع حركات المخزون ===")
for r in x.execute("""
SELECT id,product_id,warehouse_id,movement_type,
       quantity,unit_cost,reference_type,reference_id,notes
FROM stock_movements
ORDER BY id
"""):
    print(r)

print("\n=== المنتجات ذات الرصيد ===")
for r in x.execute("""
SELECT s.product_id,p.name_ar,s.quantity,s.average_cost,
       s.quantity*s.average_cost
FROM stock s
JOIN products p ON p.id=s.product_id
WHERE s.quantity<>0
ORDER BY s.product_id
"""):
    print(r)

print("\n=== إجمالي قيمة حركات المخزون ===")
r=x.execute("""
SELECT
COALESCE(SUM(CASE WHEN quantity>0 THEN quantity*unit_cost ELSE 0 END),0),
COALESCE(SUM(CASE WHEN quantity<0 THEN ABS(quantity)*unit_cost ELSE 0 END),0)
FROM stock_movements
""").fetchone()
print("قيمة الوارد:",r[0])
print("قيمة الصادر:",r[1])

print("\n=== القيود المرتبطة بالمخزون ===")
for r in x.execute("""
SELECT je.id,je.entry_number,je.description,
       a.account_code,a.account_name,j.debit,j.credit
FROM journal_entries je
JOIN journal_entry_lines j ON j.journal_entry_id=je.id
JOIN accounts a ON a.id=j.account_id
WHERE a.account_code IN ('1400','5100')
ORDER BY je.id,j.id
"""):
    print(r)

c.close()
