import sqlite3
c=sqlite3.connect(r"database\nizam_alqirtasiyah.db")
print("=== PRODUCTS ===")
for r in c.execute("PRAGMA table_info(products)"):
    print(r[1], "|", r[2], "| NOT NULL:", r[3])
c.close()
