import sqlite3
db="database/nizam_alqirtasiyah.db"
c=sqlite3.connect(db)
print("="*80)
print("NIZAM ALQIRTASIYAH — COMPLETE DATABASE SCHEMA")
print("="*80)
tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
for t in tables:
    count=c.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
    cols=c.execute(f'PRAGMA table_info("{t}")').fetchall()
    print(f"\n[{t}]  RECORDS={count}")
    print("COLUMNS:", ", ".join(x[1] for x in cols))
print("\n"+"="*80)
print("TOTAL TABLES:",len(tables))
print("="*80)
c.close()
