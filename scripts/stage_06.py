from pathlib import Path
import sqlite3,json
from datetime import datetime

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/"database"/"nizam_alqirtasiyah.db"
c=sqlite3.connect(DB)
c.execute("PRAGMA foreign_keys=ON")

c.executescript("""
CREATE TABLE IF NOT EXISTS customer_groups(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name VARCHAR(150) NOT NULL UNIQUE,
 discount_percent NUMERIC NOT NULL DEFAULT 0,
 price_type VARCHAR(50) DEFAULT 'retail',
 is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS customers(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 customer_code VARCHAR(100) NOT NULL UNIQUE,
 name VARCHAR(250) NOT NULL,
 customer_type VARCHAR(50) NOT NULL DEFAULT 'individual',
 group_id INTEGER,
 phone VARCHAR(50),
 email VARCHAR(200),
 tax_number VARCHAR(100),
 credit_limit NUMERIC NOT NULL DEFAULT 0,
 opening_balance NUMERIC NOT NULL DEFAULT 0,
 current_balance NUMERIC NOT NULL DEFAULT 0,
 is_active INTEGER NOT NULL DEFAULT 1,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(group_id) REFERENCES customer_groups(id)
);

CREATE TABLE IF NOT EXISTS customer_addresses(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 customer_id INTEGER NOT NULL,
 address_type VARCHAR(50) DEFAULT 'main',
 address TEXT NOT NULL,
 city VARCHAR(100),
 district VARCHAR(100),
 postal_code VARCHAR(30),
 FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS customer_credit_limits(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 customer_id INTEGER NOT NULL,
 old_limit NUMERIC NOT NULL DEFAULT 0,
 new_limit NUMERIC NOT NULL DEFAULT 0,
 reason TEXT,
 approved_by INTEGER,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(customer_id) REFERENCES customers(id),
 FOREIGN KEY(approved_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS customer_transactions(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 customer_id INTEGER NOT NULL,
 transaction_type VARCHAR(50) NOT NULL,
 amount NUMERIC NOT NULL,
 reference_type VARCHAR(100),
 reference_id INTEGER,
 balance_after NUMERIC NOT NULL DEFAULT 0,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(customer_id) REFERENCES customers(id)
);

CREATE TABLE IF NOT EXISTS customer_payments(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 customer_id INTEGER NOT NULL,
 amount NUMERIC NOT NULL,
 payment_method VARCHAR(50) NOT NULL,
 reference_number VARCHAR(200),
 notes TEXT,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(customer_id) REFERENCES customers(id)
);

CREATE TABLE IF NOT EXISTS customer_notes(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 customer_id INTEGER NOT NULL,
 user_id INTEGER,
 note TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(customer_id) REFERENCES customers(id),
 FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(name);
CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone);
CREATE INDEX IF NOT EXISTS idx_customer_transactions_customer ON customer_transactions(customer_id);
""")

for name,discount,price in [
("أفراد",0,"retail"),
("مدارس",5,"school"),
("شركات",3,"corporate"),
("جملة",8,"wholesale")
]:
    c.execute("""
    INSERT OR IGNORE INTO customer_groups
    (name,discount_percent,price_type)
    VALUES(?,?,?)
    """,(name,discount,price))

c.commit()

required=["customer_groups","customers","customer_addresses","customer_credit_limits","customer_transactions","customer_payments","customer_notes"]
existing={x[0] for x in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
missing=[x for x in required if x not in existing]
if missing: raise RuntimeError("جداول ناقصة: "+",".join(missing))
if c.execute("PRAGMA integrity_check").fetchone()[0]!="ok": raise RuntimeError("فشل integrity_check")

c.close()

sf=ROOT/".lulu_state"/"build_state.json"
state=json.loads(sf.read_text(encoding="utf-8"))
state["last_completed_stage"]=6
state["last_completed_at"]=datetime.now().isoformat()
sf.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding="utf-8")

print("CUSTOMERS: OK")
print("CUSTOMER GROUPS: OK")
print("CREDIT LIMITS: OK")
print("CUSTOMER TRANSACTIONS: OK")
print("CUSTOMER PAYMENTS: OK")
print("CRM STRUCTURE: OK")
print("INTEGRITY: OK")
print("STATE: UPDATED")
print("STATUS: SUCCESS")
