import sqlite3
c=sqlite3.connect(r"database\nizam_alqirtasiyah.db")

for t in ["stock","stock_movements","sale_items","purchase_invoice_items"]:
    print("\n===" + t + " ===")
    try:
        for r in c.execute(f'PRAGMA table_info("{t}")').fetchall():
            print(f"{r[1]} | {r[2]} | NOT NULL:{r[3]} | DEFAULT:{r[4]}")
    except Exception as e:
        print("غير موجود:",e)

c.close()
