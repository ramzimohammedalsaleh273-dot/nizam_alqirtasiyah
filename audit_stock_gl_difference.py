import sqlite3

DB=r"database\nizam_alqirtasiyah.db"
c=sqlite3.connect(DB)
x=c.cursor()

print("="*70)
print("فحص الفرق بين المخزون الفعلي والمحاسبي")
print("="*70)

print("\n=== حركات المخزون الحالية ===")
for r in x.execute("""
SELECT id, product_id, movement_type, quantity, unit_cost,
       reference_type, reference_id, notes
FROM stock_movements
ORDER BY id
"""):
    print(r)

print("\n=== قيمة المخزون الحالية ===")
r=x.execute("""
SELECT
    COALESCE(SUM(quantity),0),
    COALESCE(SUM(quantity*average_cost),0)
FROM stock
""").fetchone()
print("الكمية:",r[0])
print("القيمة:",r[1])

print("\n=== قيود حساب المخزون 1400 ===")
for r in x.execute("""
SELECT je.id, je.entry_number, je.description,
       j.debit, j.credit
FROM journal_entries je
JOIN journal_entry_lines j ON j.journal_entry_id=je.id
JOIN accounts a ON a.id=j.account_id
WHERE a.account_code='1400'
ORDER BY je.id
"""):
    print(r)

print("\n=== رصيد الحساب 1400 ===")
r=x.execute("""
SELECT COALESCE(SUM(j.debit),0)-COALESCE(SUM(j.credit),0)
FROM journal_entry_lines j
JOIN accounts a ON a.id=j.account_id
WHERE a.account_code='1400'
""").fetchone()
print("رصيد 1400:",r[0])

print("\n=== مقارنة المنتجات ===")
for r in x.execute("""
SELECT s.product_id,p.name_ar,s.quantity,s.average_cost,
       s.quantity*s.average_cost AS stock_value
FROM stock s
JOIN products p ON p.id=s.product_id
WHERE s.quantity<>0
ORDER BY s.product_id
"""):
    print(r)

print("\n=== سلامة القاعدة ===")
print("SQLite:",x.execute("PRAGMA integrity_check").fetchone()[0])
print("Foreign Keys:",len(x.execute("PRAGMA foreign_key_check").fetchall()))

c.close()
