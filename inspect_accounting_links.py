import sqlite3

c=sqlite3.connect(r"database\nizam_alqirtasiyah.db")
x=c.cursor()

for t in ["journal_entries","journal_entry_lines","accounts"]:
    print("\n===" + t + " ===")
    try:
        for r in x.execute(f'PRAGMA table_info("{t}")').fetchall():
            print(f"{r[1]} | {r[2]} | NOT NULL:{r[3]} | DEFAULT:{r[4]}")
    except Exception as e:
        print("غير موجود:",e)

print("\n=== آخر القيود المحاسبية ===")
try:
    rows=x.execute("SELECT * FROM journal_entries ORDER BY id DESC LIMIT 10").fetchall()
    for r in rows:
        print(r)
except Exception as e:
    print("تعذر القراءة:",e)

print("\n=== أرصدة الحسابات ===")
try:
    rows=x.execute("""
    SELECT a.id,a.code,a.name_ar,
           COALESCE(SUM(jel.debit),0),
           COALESCE(SUM(jel.credit),0)
    FROM accounts a
    LEFT JOIN journal_entry_lines jel ON jel.account_id=a.id
    GROUP BY a.id,a.code,a.name_ar
    ORDER BY a.id
    """).fetchall()
    for r in rows:
        print(r)
except Exception as e:
    print("تعذر حساب الأرصدة:",e)

c.close()
