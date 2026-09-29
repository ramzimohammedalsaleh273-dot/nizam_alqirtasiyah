import sqlite3
from pathlib import Path

db = Path("database") / "nizam_alqirtasiyah.db"
con = sqlite3.connect(db)

tables = con.execute("""
SELECT name
FROM sqlite_master
WHERE type='table'
AND name NOT LIKE 'sqlite_%'
ORDER BY name
""").fetchall()

print("=" * 70)
print("فحص قاعدة بيانات نظام القرطاسية")
print("=" * 70)
print("عدد الجداول:", len(tables))
print()

for (name,) in tables:
    try:
        count = con.execute(
            'SELECT COUNT(*) FROM "' + name.replace('"', '""') + '"'
        ).fetchone()[0]
        print(f"{name:<35} السجلات: {count}")
    except Exception as e:
        print(f"{name:<35} خطأ: {e}")

print()
print("=" * 70)
print("DATABASE CHECK: COMPLETED")
print("=" * 70)

con.close()
