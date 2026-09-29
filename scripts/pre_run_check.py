
from pathlib import Path
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/"database"/"nizam_alqirtasiyah.db"

print("="*60)
print("نظام القرطاسية - PRE RUN CHECK")
print("="*60)

if not DB.exists():
    print("STATUS: FAILED - DATABASE NOT FOUND")
    sys.exit(1)

con=sqlite3.connect(DB)
cur=con.cursor()

integrity=cur.execute("PRAGMA integrity_check").fetchone()[0]

tables=[
    "products","suppliers","warehouses",
    "sales","purchase_orders",
    "stock_movements",
    "journal_entries",
    "journal_entry_lines"
]

ok=True

print("DATABASE:",DB)
print("INTEGRITY:",integrity)

for table in tables:
    exists=cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,)
    ).fetchone()

    print(table,":","OK" if exists else "MISSING")

    if not exists:
        ok=False

con.close()

print("="*60)
print("STATUS:", "READY" if ok and integrity=="ok" else "FAILED")
print("="*60)

sys.exit(0 if ok and integrity=="ok" else 1)
