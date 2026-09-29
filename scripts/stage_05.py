from pathlib import Path
import sqlite3,json
from datetime import datetime

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/"database"/"nizam_alqirtasiyah.db"
c=sqlite3.connect(DB)
c.execute("PRAGMA foreign_keys=ON")

c.executescript("""
CREATE TABLE IF NOT EXISTS sales(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 invoice_number VARCHAR(100) NOT NULL UNIQUE,
 branch_id INTEGER NOT NULL,
 warehouse_id INTEGER,
 customer_id INTEGER,
 cashier_id INTEGER,
 status VARCHAR(50) NOT NULL DEFAULT 'completed',
 subtotal NUMERIC NOT NULL DEFAULT 0,
 discount_amount NUMERIC NOT NULL DEFAULT 0,
 tax_amount NUMERIC NOT NULL DEFAULT 0,
 total_amount NUMERIC NOT NULL DEFAULT 0,
 paid_amount NUMERIC NOT NULL DEFAULT 0,
 due_amount NUMERIC NOT NULL DEFAULT 0,
 notes TEXT,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(branch_id) REFERENCES branches(id),
 FOREIGN KEY(warehouse_id) REFERENCES warehouses(id),
 FOREIGN KEY(customer_id) REFERENCES customers(id),
 FOREIGN KEY(cashier_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS sale_items(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 sale_id INTEGER NOT NULL,
 product_id INTEGER NOT NULL,
 quantity NUMERIC NOT NULL,
 unit_price NUMERIC NOT NULL,
 discount_amount NUMERIC NOT NULL DEFAULT 0,
 tax_amount NUMERIC NOT NULL DEFAULT 0,
 line_total NUMERIC NOT NULL DEFAULT 0,
 FOREIGN KEY(sale_id) REFERENCES sales(id) ON DELETE CASCADE,
 FOREIGN KEY(product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS sale_payments(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 sale_id INTEGER NOT NULL,
 payment_method VARCHAR(50) NOT NULL,
 amount NUMERIC NOT NULL,
 reference_number VARCHAR(200),
 notes TEXT,
 FOREIGN KEY(sale_id) REFERENCES sales(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sale_returns(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 return_number VARCHAR(100) NOT NULL UNIQUE,
 sale_id INTEGER NOT NULL,
 customer_id INTEGER,
 reason TEXT,
 status VARCHAR(50) NOT NULL DEFAULT 'completed',
 total_amount NUMERIC NOT NULL DEFAULT 0,
 created_by INTEGER,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(sale_id) REFERENCES sales(id),
 FOREIGN KEY(customer_id) REFERENCES customers(id),
 FOREIGN KEY(created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS sale_return_items(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 return_id INTEGER NOT NULL,
 sale_item_id INTEGER,
 product_id INTEGER NOT NULL,
 quantity NUMERIC NOT NULL,
 unit_price NUMERIC NOT NULL,
 total_amount NUMERIC NOT NULL DEFAULT 0,
 FOREIGN KEY(return_id) REFERENCES sale_returns(id) ON DELETE CASCADE,
 FOREIGN KEY(sale_item_id) REFERENCES sale_items(id),
 FOREIGN KEY(product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS held_sales(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 hold_number VARCHAR(100) NOT NULL UNIQUE,
 branch_id INTEGER NOT NULL,
 cashier_id INTEGER,
 customer_id INTEGER,
 data_json TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(branch_id) REFERENCES branches(id),
 FOREIGN KEY(cashier_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS cash_registers(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 branch_id INTEGER NOT NULL,
 name VARCHAR(100) NOT NULL,
 code VARCHAR(50) NOT NULL UNIQUE,
 is_active INTEGER NOT NULL DEFAULT 1,
 FOREIGN KEY(branch_id) REFERENCES branches(id)
);

CREATE TABLE IF NOT EXISTS cash_sessions(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 register_id INTEGER NOT NULL,
 user_id INTEGER NOT NULL,
 opening_balance NUMERIC NOT NULL DEFAULT 0,
 expected_balance NUMERIC NOT NULL DEFAULT 0,
 actual_balance NUMERIC,
 difference NUMERIC,
 opened_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 closed_at TEXT,
 status VARCHAR(30) NOT NULL DEFAULT 'open',
 FOREIGN KEY(register_id) REFERENCES cash_registers(id),
 FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS cash_transactions(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 cash_session_id INTEGER,
 transaction_type VARCHAR(50) NOT NULL,
 amount NUMERIC NOT NULL,
 reference_type VARCHAR(100),
 reference_id INTEGER,
 notes TEXT,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(cash_session_id) REFERENCES cash_sessions(id)
);

CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(created_at);
CREATE INDEX IF NOT EXISTS idx_sales_invoice ON sales(invoice_number);
CREATE INDEX IF NOT EXISTS idx_sale_items_product ON sale_items(product_id);
""")

branch=c.execute("SELECT id FROM branches WHERE code='MAIN'").fetchone()[0]
c.execute("""
INSERT OR IGNORE INTO cash_registers(branch_id,name,code)
VALUES(?,?,?)
""",(branch,"الكاشير الرئيسي","MAIN-CASH"))

c.commit()

required=["sales","sale_items","sale_payments","sale_returns","sale_return_items","held_sales","cash_registers","cash_sessions","cash_transactions"]
existing={x[0] for x in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
missing=[x for x in required if x not in existing]
if missing: raise RuntimeError("جداول ناقصة: "+",".join(missing))
if c.execute("PRAGMA integrity_check").fetchone()[0]!="ok": raise RuntimeError("فشل integrity_check")

c.close()

sf=ROOT/".lulu_state"/"build_state.json"
state=json.loads(sf.read_text(encoding="utf-8"))
state["last_completed_stage"]=5
state["last_completed_at"]=datetime.now().isoformat()
sf.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding="utf-8")

print("POS: OK")
print("SALES: OK")
print("PAYMENTS: OK")
print("RETURNS: OK")
print("HELD SALES: OK")
print("CASH REGISTER STRUCTURE: OK")
print("INTEGRITY: OK")
print("STATE: UPDATED")
print("STATUS: SUCCESS")
