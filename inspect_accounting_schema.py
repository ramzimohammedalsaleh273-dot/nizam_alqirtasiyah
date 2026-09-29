import sqlite3
from pathlib import Path

db = Path("database/nizam_alqirtasiyah.db")
con = sqlite3.connect(db)

print("=" * 70)
print("فحص جداول التكامل المحاسبي")
print("=" * 70)

tables = [
    "sales",
    "sale_items",
    "sale_payments",
    "customer_transactions",
    "customer_payments",
    "journal_entries",
    "journal_entry_lines",
    "accounts",
    "stock",
    "stock_movements",
    "purchase_invoices",
    "purchase_invoice_items",
]

existing = {
    r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
}

for table in tables:
    print()
    print("-" * 70)
    print(f"TABLE: {table}")

    if table not in existing:
        print("[غير موجود]")
        continue

    rows = con.execute(f"PRAGMA table_info({table})").fetchall()

    for row in rows:
        cid, name, typ, notnull, default, pk = row
        print(
            f"{cid}: {name} | {typ} | "
            f"NOT NULL={notnull} | DEFAULT={default} | PK={pk}"
        )

print()
print("=" * 70)
print("الحسابات المحاسبية الحالية")
print("=" * 70)

for row in con.execute("""
    SELECT account_code, account_name, account_type,
           opening_balance, is_active, allow_posting
    FROM accounts
    ORDER BY account_code
"""):
    print(row)

print()
print("=" * 70)
print("أحدث قيود اليومية")
print("=" * 70)

for row in con.execute("""
    SELECT id, entry_number, entry_date,
           description, source_type, source_id, status
    FROM journal_entries
    ORDER BY id DESC
    LIMIT 10
"""):
    print(row)

print()
print("=" * 70)
print("فحص سلامة SQLite")
print("=" * 70)
print("SQLite:", con.execute("PRAGMA integrity_check").fetchone()[0])
print("Foreign Keys:", len(con.execute("PRAGMA foreign_key_check").fetchall()))

con.close()
