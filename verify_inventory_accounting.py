import sqlite3

c=sqlite3.connect(r"database\nizam_alqirtasiyah.db")
x=c.cursor()

print("=== ملخص المخزون ===")

r=x.execute("""
SELECT
    COUNT(*),
    COALESCE(SUM(quantity),0),
    COALESCE(SUM(quantity*average_cost),0)
FROM stock
""").fetchone()

print("عدد أصناف المخزون :",r[0])
print("إجمالي الكمية     :",r[1])
print("قيمة المخزون       :",r[2])

print("\n=== حسب المستودع ===")

for r in x.execute("""
SELECT
    w.id,
    w.name,
    COUNT(s.id),
    COALESCE(SUM(s.quantity),0),
    COALESCE(SUM(s.quantity*s.average_cost),0)
FROM warehouses w
LEFT JOIN stock s ON s.warehouse_id=w.id
GROUP BY w.id,w.name
ORDER BY w.id
"""):
    print(r)

print("\n=== حركات المخزون ===")

for r in x.execute("""
SELECT
    movement_type,
    COUNT(*),
    COALESCE(SUM(quantity),0)
FROM stock_movements
GROUP BY movement_type
ORDER BY movement_type
"""):
    print(r)

print("\n=== مقارنة الحساب 1400 ===")

r=x.execute("""
SELECT
    COALESCE(SUM(debit),0),
    COALESCE(SUM(credit),0),
    COALESCE(SUM(debit),0)-COALESCE(SUM(credit),0)
FROM journal_entry_lines jel
JOIN accounts a ON a.id=jel.account_id
WHERE a.account_code='1400'
""").fetchone()

print("مدين المخزون :",r[0])
print("دائن المخزون :",r[1])
print("رصيد 1400    :",r[2])

print("\n=== تكلفة البضاعة المباعة 5100 ===")

r=x.execute("""
SELECT
    COALESCE(SUM(debit),0),
    COALESCE(SUM(credit),0)
FROM journal_entry_lines jel
JOIN accounts a ON a.id=jel.account_id
WHERE a.account_code='5100'
""").fetchone()

print("مدين:",r[0])
print("دائن:",r[1])

c.close()
