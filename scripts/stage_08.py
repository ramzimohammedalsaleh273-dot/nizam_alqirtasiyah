from pathlib import Path
import sqlite3,json
from datetime import datetime

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/"database"/"nizam_alqirtasiyah.db"
c=sqlite3.connect(DB)
c.execute("PRAGMA foreign_keys=ON")

c.executescript("""
CREATE TABLE IF NOT EXISTS supplier_groups(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name VARCHAR(150) NOT NULL UNIQUE,
 description TEXT
);

CREATE TABLE IF NOT EXISTS suppliers(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 supplier_code VARCHAR(100) NOT NULL UNIQUE,
 name VARCHAR(250) NOT NULL,
 supplier_type VARCHAR(50) NOT NULL DEFAULT 'local',
 phone VARCHAR(50),
 email VARCHAR(200),
 tax_number VARCHAR(100),
 address VARCHAR(500),
 credit_limit NUMERIC NOT NULL DEFAULT 0,
 current_balance NUMERIC NOT NULL DEFAULT 0,
 group_id INTEGER,
 is_active INTEGER NOT NULL DEFAULT 1,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(group_id) REFERENCES supplier_groups(id)
);

CREATE TABLE IF NOT EXISTS supplier_products(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 supplier_id INTEGER NOT NULL,
 product_id INTEGER NOT NULL,
 supplier_sku VARCHAR(100),
 preferred INTEGER NOT NULL DEFAULT 0,
 UNIQUE(supplier_id,product_id),
 FOREIGN KEY(supplier_id) REFERENCES suppliers(id),
 FOREIGN KEY(product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS supplier_prices(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 supplier_id INTEGER NOT NULL,
 product_id INTEGER NOT NULL,
 price NUMERIC NOT NULL DEFAULT 0,
 minimum_quantity NUMERIC NOT NULL DEFAULT 1,
 valid_from TEXT,
 valid_to TEXT,
 FOREIGN KEY(supplier_id) REFERENCES suppliers(id),
 FOREIGN KEY(product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS supplier_evaluations(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 supplier_id INTEGER NOT NULL,
 quality_score NUMERIC,
 price_score NUMERIC,
 delivery_score NUMERIC,
 shortage_score NUMERIC,
 notes TEXT,
 evaluated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(supplier_id) REFERENCES suppliers(id)
);

CREATE TABLE IF NOT EXISTS purchase_requests(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 request_number VARCHAR(100) NOT NULL UNIQUE,
 branch_id INTEGER NOT NULL,
 requested_by INTEGER,
 status VARCHAR(50) NOT NULL DEFAULT 'draft',
 notes TEXT,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(branch_id) REFERENCES branches(id),
 FOREIGN KEY(requested_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS purchase_request_items(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 request_id INTEGER NOT NULL,
 product_id INTEGER NOT NULL,
 quantity NUMERIC NOT NULL,
 estimated_cost NUMERIC NOT NULL DEFAULT 0,
 FOREIGN KEY(request_id) REFERENCES purchase_requests(id) ON DELETE CASCADE,
 FOREIGN KEY(product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS purchase_orders(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 order_number VARCHAR(100) NOT NULL UNIQUE,
 branch_id INTEGER NOT NULL,
 supplier_id INTEGER NOT NULL,
 status VARCHAR(50) NOT NULL DEFAULT 'draft',
 subtotal NUMERIC NOT NULL DEFAULT 0,
 discount_amount NUMERIC NOT NULL DEFAULT 0,
 tax_amount NUMERIC NOT NULL DEFAULT 0,
 total_amount NUMERIC NOT NULL DEFAULT 0,
 notes TEXT,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(branch_id) REFERENCES branches(id),
 FOREIGN KEY(supplier_id) REFERENCES suppliers(id)
);

CREATE TABLE IF NOT EXISTS purchase_order_items(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 order_id INTEGER NOT NULL,
 product_id INTEGER NOT NULL,
 quantity NUMERIC NOT NULL,
 unit_cost NUMERIC NOT NULL DEFAULT 0,
 tax_amount NUMERIC NOT NULL DEFAULT 0,
 line_total NUMERIC NOT NULL DEFAULT 0,
 FOREIGN KEY(order_id) REFERENCES purchase_orders(id) ON DELETE CASCADE,
 FOREIGN KEY(product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS goods_receipts(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 receipt_number VARCHAR(100) NOT NULL UNIQUE,
 purchase_order_id INTEGER,
 warehouse_id INTEGER NOT NULL,
 supplier_id INTEGER NOT NULL,
 status VARCHAR(50) NOT NULL DEFAULT 'received',
 received_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 notes TEXT,
 FOREIGN KEY(purchase_order_id) REFERENCES purchase_orders(id),
 FOREIGN KEY(warehouse_id) REFERENCES warehouses(id),
 FOREIGN KEY(supplier_id) REFERENCES suppliers(id)
);

CREATE TABLE IF NOT EXISTS goods_receipt_items(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 receipt_id INTEGER NOT NULL,
 product_id INTEGER NOT NULL,
 ordered_quantity NUMERIC NOT NULL DEFAULT 0,
 received_quantity NUMERIC NOT NULL DEFAULT 0,
 rejected_quantity NUMERIC NOT NULL DEFAULT 0,
 unit_cost NUMERIC NOT NULL DEFAULT 0,
 FOREIGN KEY(receipt_id) REFERENCES goods_receipts(id) ON DELETE CASCADE,
 FOREIGN KEY(product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS purchase_invoices(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 invoice_number VARCHAR(100) NOT NULL UNIQUE,
 supplier_id INTEGER NOT NULL,
 purchase_order_id INTEGER,
 subtotal NUMERIC NOT NULL DEFAULT 0,
 tax_amount NUMERIC NOT NULL DEFAULT 0,
 total_amount NUMERIC NOT NULL DEFAULT 0,
 paid_amount NUMERIC NOT NULL DEFAULT 0,
 due_amount NUMERIC NOT NULL DEFAULT 0,
 status VARCHAR(50) NOT NULL DEFAULT 'open',
 invoice_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 due_date TEXT,
 FOREIGN KEY(supplier_id) REFERENCES suppliers(id),
 FOREIGN KEY(purchase_order_id) REFERENCES purchase_orders(id)
);

CREATE TABLE IF NOT EXISTS purchase_invoice_items(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 invoice_id INTEGER NOT NULL,
 product_id INTEGER NOT NULL,
 quantity NUMERIC NOT NULL,
 unit_cost NUMERIC NOT NULL DEFAULT 0,
 tax_amount NUMERIC NOT NULL DEFAULT 0,
 line_total NUMERIC NOT NULL DEFAULT 0,
 FOREIGN KEY(invoice_id) REFERENCES purchase_invoices(id) ON DELETE CASCADE,
 FOREIGN KEY(product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS purchase_returns(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 return_number VARCHAR(100) NOT NULL UNIQUE,
 supplier_id INTEGER NOT NULL,
 invoice_id INTEGER,
 reason TEXT,
 total_amount NUMERIC NOT NULL DEFAULT 0,
 status VARCHAR(50) NOT NULL DEFAULT 'completed',
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(supplier_id) REFERENCES suppliers(id),
 FOREIGN KEY(invoice_id) REFERENCES purchase_invoices(id)
);

CREATE INDEX IF NOT EXISTS idx_suppliers_name ON suppliers(name);
CREATE INDEX IF NOT EXISTS idx_purchase_orders_supplier ON purchase_orders(supplier_id);
CREATE INDEX IF NOT EXISTS idx_purchase_invoices_supplier ON purchase_invoices(supplier_id);
""")

c.execute("INSERT OR IGNORE INTO supplier_groups(name) VALUES ('الموردون المحليون')")
c.execute("INSERT OR IGNORE INTO supplier_groups(name) VALUES ('الموردون الدوليون')")
c.commit()

required=["supplier_groups","suppliers","supplier_products","supplier_prices","supplier_evaluations","purchase_requests","purchase_request_items","purchase_orders","purchase_order_items","goods_receipts","goods_receipt_items","purchase_invoices","purchase_invoice_items","purchase_returns"]
existing={x[0] for x in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
missing=[x for x in required if x not in existing]
if missing: raise RuntimeError("جداول ناقصة: "+",".join(missing))
if c.execute("PRAGMA integrity_check").fetchone()[0]!="ok": raise RuntimeError("فشل integrity_check")

c.close()

sf=ROOT/".lulu_state"/"build_state.json"
state=json.loads(sf.read_text(encoding="utf-8"))
state["last_completed_stage"]=8
state["last_completed_at"]=datetime.now().isoformat()
sf.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding="utf-8")

print("SUPPLIERS: OK")
print("PURCHASE REQUESTS: OK")
print("PURCHASE ORDERS: OK")
print("GOODS RECEIVING: OK")
print("PURCHASE INVOICES: OK")
print("PURCHASE RETURNS: OK")
print("INTEGRITY: OK")
print("STATE: UPDATED")
print("STATUS: SUCCESS")
