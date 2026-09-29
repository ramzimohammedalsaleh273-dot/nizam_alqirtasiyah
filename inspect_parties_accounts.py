import sqlite3

c=sqlite3.connect(r"database\nizam_alqirtasiyah.db")
x=c.cursor()

for t in ["customers","suppliers"]:
    print("\n===" + t + " ===")
    for r in x.execute(f'PRAGMA table_info("{t}")').fetchall():
        print(f"{r[1]} | {r[2]} | NOT NULL:{r[3]} | DEFAULT:{r[4]}")

print("\n=== الحساب 1300 ===")
print(x.execute("""
SELECT id,account_code,account_name,account_type,parent_id
FROM accounts WHERE account_code='1300'
""").fetchall())

print("\n=== الحساب 2100 ===")
print(x.execute("""
SELECT id,account_code,account_name,account_type,parent_id
FROM accounts WHERE account_code='2100'
""").fetchall())

c.close()
