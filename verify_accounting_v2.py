import sqlite3

c=sqlite3.connect(r"database\nizam_alqirtasiyah.db")
x=c.cursor()

print("=== تفاصيل القيود المحاسبية ===")

rows=x.execute("""
SELECT
    je.id,
    je.entry_number,
    je.description,
    je.source_type,
    je.source_id,
    jel.account_id,
    a.account_code,
    a.account_name,
    jel.debit,
    jel.credit
FROM journal_entries je
JOIN journal_entry_lines jel
    ON jel.journal_entry_id=je.id
JOIN accounts a
    ON a.id=jel.account_id
ORDER BY je.id,jel.id
""").fetchall()

for r in rows:
    print(r)

print("\n=== إجمالي المدين والدائن ===")

r=x.execute("""
SELECT
    COALESCE(SUM(debit),0),
    COALESCE(SUM(credit),0),
    COALESCE(SUM(debit),0)-COALESCE(SUM(credit),0)
FROM journal_entry_lines
""").fetchone()

print("المدين :",r[0])
print("الدائن :",r[1])
print("الفرق  :",r[2])

print("\n=== أرصدة الحسابات ===")

rows=x.execute("""
SELECT
    a.account_code,
    a.account_name,
    COALESCE(SUM(j.debit),0),
    COALESCE(SUM(j.credit),0),
    COALESCE(SUM(j.debit),0)-COALESCE(SUM(j.credit),0)
FROM accounts a
LEFT JOIN journal_entry_lines j
    ON j.account_id=a.id
GROUP BY a.id,a.account_code,a.account_name
ORDER BY a.account_code
""").fetchall()

for r in rows:
    print(r)

c.close()
