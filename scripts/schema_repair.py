import sqlite3
from pathlib import Path

DB = Path("database/nizam_alqirtasiyah.db")
con = sqlite3.connect(DB)
con.execute("PRAGMA foreign_keys=ON")

# إصلاح أعمدة الربط الناقصة
cols = lambda t: {r[1] for r in con.execute(f'PRAGMA table_info("{t}")')}

if "purchase_order_id" not in cols("purchase_order_items"):
    con.execute("ALTER TABLE purchase_order_items ADD COLUMN purchase_order_id INTEGER")

if "purchase_invoice_id" not in cols("purchase_invoice_items"):
    con.execute("ALTER TABLE purchase_invoice_items ADD COLUMN purchase_invoice_id INTEGER")

# إنشاء سجل تدقيق موحد إذا لم يكن موجودًا
if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='audit_log'").fetchone():
    con.execute("""
        CREATE TABLE audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action VARCHAR(100) NOT NULL,
            table_name VARCHAR(100),
            record_id INTEGER,
            description TEXT,
            old_values TEXT,
            new_values TEXT,
            ip_address VARCHAR(100),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

con.commit()

print("PURCHASE ORDER LINK: OK")
print("PURCHASE INVOICE LINK: OK")
print("AUDIT LOG: OK")

for t in ["purchase_order_items","purchase_invoice_items","audit_log"]:
    print(t, "=>", con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0])

print("STATUS: SCHEMA REPAIR SUCCESS")
con.close()
