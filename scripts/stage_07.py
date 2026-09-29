from pathlib import Path
import sqlite3,json
from datetime import datetime

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/"database"/"nizam_alqirtasiyah.db"
c=sqlite3.connect(DB)
c.execute("PRAGMA foreign_keys=ON")

c.executescript("""
CREATE TABLE IF NOT EXISTS loyalty_accounts(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 customer_id INTEGER NOT NULL UNIQUE,
 points_balance NUMERIC NOT NULL DEFAULT 0,
 tier VARCHAR(50) NOT NULL DEFAULT 'basic',
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(customer_id) REFERENCES customers(id)
);

CREATE TABLE IF NOT EXISTS loyalty_transactions(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 loyalty_account_id INTEGER NOT NULL,
 transaction_type VARCHAR(50) NOT NULL,
 points NUMERIC NOT NULL,
 reference_type VARCHAR(100),
 reference_id INTEGER,
 balance_after NUMERIC NOT NULL DEFAULT 0,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(loyalty_account_id) REFERENCES loyalty_accounts(id)
);

CREATE TABLE IF NOT EXISTS loyalty_rules(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name VARCHAR(200) NOT NULL,
 points_per_currency NUMERIC NOT NULL DEFAULT 0,
 minimum_purchase NUMERIC NOT NULL DEFAULT 0,
 points_value NUMERIC NOT NULL DEFAULT 0,
 is_active INTEGER NOT NULL DEFAULT 1,
 start_date TEXT,
 end_date TEXT
);

CREATE TABLE IF NOT EXISTS promotions(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name VARCHAR(200) NOT NULL,
 promotion_type VARCHAR(50) NOT NULL,
 value NUMERIC NOT NULL DEFAULT 0,
 minimum_amount NUMERIC NOT NULL DEFAULT 0,
 maximum_discount NUMERIC,
 start_date TEXT,
 end_date TEXT,
 is_active INTEGER NOT NULL DEFAULT 1,
 description TEXT
);

CREATE TABLE IF NOT EXISTS promotion_items(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 promotion_id INTEGER NOT NULL,
 product_id INTEGER,
 category_id INTEGER,
 minimum_quantity NUMERIC NOT NULL DEFAULT 1,
 FOREIGN KEY(promotion_id) REFERENCES promotions(id) ON DELETE CASCADE,
 FOREIGN KEY(product_id) REFERENCES products(id),
 FOREIGN KEY(category_id) REFERENCES product_categories(id)
);

CREATE TABLE IF NOT EXISTS coupons(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 code VARCHAR(100) NOT NULL UNIQUE,
 promotion_id INTEGER,
 usage_limit INTEGER,
 used_count INTEGER NOT NULL DEFAULT 0,
 start_date TEXT,
 end_date TEXT,
 is_active INTEGER NOT NULL DEFAULT 1,
 FOREIGN KEY(promotion_id) REFERENCES promotions(id)
);

CREATE TABLE IF NOT EXISTS coupon_redemptions(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 coupon_id INTEGER NOT NULL,
 customer_id INTEGER,
 sale_id INTEGER,
 discount_amount NUMERIC NOT NULL DEFAULT 0,
 redeemed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(coupon_id) REFERENCES coupons(id),
 FOREIGN KEY(customer_id) REFERENCES customers(id),
 FOREIGN KEY(sale_id) REFERENCES sales(id)
);

CREATE INDEX IF NOT EXISTS idx_loyalty_customer ON loyalty_accounts(customer_id);
CREATE INDEX IF NOT EXISTS idx_coupon_code ON coupons(code);
CREATE INDEX IF NOT EXISTS idx_promotions_dates ON promotions(start_date,end_date);
""")

c.execute("""
INSERT OR IGNORE INTO loyalty_rules
(name,points_per_currency,minimum_purchase,points_value)
VALUES ('النظام الأساسي',1,1,0.01)
""")

c.commit()

required=["loyalty_accounts","loyalty_transactions","loyalty_rules","promotions","promotion_items","coupons","coupon_redemptions"]
existing={x[0] for x in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
missing=[x for x in required if x not in existing]
if missing: raise RuntimeError("جداول ناقصة: "+",".join(missing))
if c.execute("PRAGMA integrity_check").fetchone()[0]!="ok": raise RuntimeError("فشل integrity_check")

c.close()

sf=ROOT/".lulu_state"/"build_state.json"
state=json.loads(sf.read_text(encoding="utf-8"))
state["last_completed_stage"]=7
state["last_completed_at"]=datetime.now().isoformat()
sf.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding="utf-8")

print("LOYALTY: OK")
print("POINT TRANSACTIONS: OK")
print("PROMOTIONS: OK")
print("COUPONS: OK")
print("REDEMPTIONS: OK")
print("INTEGRITY: OK")
print("STATE: UPDATED")
print("STATUS: SUCCESS")
