import sqlite3

c=sqlite3.connect(r"database\nizam_alqirtasiyah.db")
x=c.cursor()

print("=== الحسابات ===")
for r in x.execute("""
SELECT id,account_code,account_name,account_type,
       parent_id,is_active,allow_posting,opening_balance
FROM accounts
ORDER BY account_code
"""):
    print(r)

print("\n=== المبيعات وتكلفة كل حركة ===")
for r in x.execute("""
SELECT id,product_id,movement_type,quantity,unit_cost,
       quantity*unit_cost AS value
FROM stock_movements
ORDER BY id
"""):
    print(r)

print("\n=== إجمالي التكلفة حسب الحركات ===")
r=x.execute("""
SELECT
COALESCE(SUM(CASE WHEN quantity>0 THEN quantity*unit_cost ELSE 0 END),0),
COALESCE(SUM(CASE WHEN quantity<0 THEN ABS(quantity)*unit_cost ELSE 0 END),0)
FROM stock_movements
""").fetchone()
print("الوارد:",r[0])
print("الصادر:",r[1])

c.close()
