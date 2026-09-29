from pathlib import Path
import sqlite3,json
from datetime import datetime

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/"database"/"nizam_alqirtasiyah.db"
c=sqlite3.connect(DB)
c.execute("PRAGMA foreign_keys=ON")

c.executescript("""
CREATE TABLE IF NOT EXISTS warehouses(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 branch_id INTEGER NOT NULL,
 name VARCHAR(200) NOT NULL,
 code VARCHAR(50) NOT NULL UNIQUE,
 warehouse_type VARCHAR(50) DEFAULT 'main',
 is_active INTEGER NOT NULL DEFAULT 1,
 FOREIGN KEY(branch_id) REFERENCES branches(id)
);

CREATE TABLE IF NOT EXISTS warehouse_zones(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 warehouse_id INTEGER NOT NULL,
 name VARCHAR(200) NOT NULL,
 code VARCHAR(50),
 FOREIGN KEY(warehouse_id) REFERENCES warehouses(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS warehouse_aisles(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 zone_id INTEGER NOT NULL,
 name VARCHAR(200) NOT NULL,
 code VARCHAR(50),
 FOREIGN KEY(zone_id) REFERENCES warehouse_zones(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS warehouse_shelves(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 aisle_id INTEGER NOT NULL,
 name VARCHAR(200) NOT NULL,
 code VARCHAR(50),
 FOREIGN KEY(aisle_id) REFERENCES warehouse_aisles(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS warehouse_bins(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 shelf_id INTEGER NOT NULL,
 name VARCHAR(200) NOT NULL,
 code VARCHAR(50),
 FOREIGN KEY(shelf_id) REFERENCES warehouse_shelves(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS product_locations(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 product_id INTEGER NOT NULL,
 warehouse_id INTEGER NOT NULL,
 bin_id INTEGER,
 quantity NUMERIC NOT NULL DEFAULT 0,
 UNIQUE(product_id,warehouse_id,bin_id),
 FOREIGN KEY(product_id) REFERENCES products(id),
 FOREIGN KEY(warehouse_id) REFERENCES warehouses(id),
 FOREIGN KEY(bin_id) REFERENCES warehouse_bins(id)
);

CREATE TABLE IF NOT EXISTS stock_balances(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 product_id INTEGER NOT NULL,
 warehouse_id INTEGER NOT NULL,
 quantity NUMERIC NOT NULL DEFAULT 0,
 reserved_quantity NUMERIC NOT NULL DEFAULT 0,
 average_cost NUMERIC NOT NULL DEFAULT 0,
 last_movement_at TEXT,
 UNIQUE(product_id,warehouse_id),
 FOREIGN KEY(product_id) REFERENCES products(id),
 FOREIGN KEY(warehouse_id) REFERENCES warehouses(id)
);

CREATE TABLE IF NOT EXISTS stock_movements(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 product_id INTEGER NOT NULL,
 warehouse_id INTEGER NOT NULL,
 movement_type VARCHAR(50) NOT NULL,
 quantity NUMERIC NOT NULL,
 unit_cost NUMERIC NOT NULL DEFAULT 0,
 reference_type VARCHAR(100),
 reference_id INTEGER,
 notes TEXT,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(product_id) REFERENCES products(id),
 FOREIGN KEY(warehouse_id) REFERENCES warehouses(id)
);

CREATE TABLE IF NOT EXISTS stocktakes(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 warehouse_id INTEGER NOT NULL,
 status VARCHAR(50) NOT NULL DEFAULT 'draft',
 started_at TEXT,
 completed_at TEXT,
 notes TEXT,
 FOREIGN KEY(warehouse_id) REFERENCES warehouses(id)
);

CREATE TABLE IF NOT EXISTS stocktake_items(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 stocktake_id INTEGER NOT NULL,
 product_id INTEGER NOT NULL,
 system_quantity NUMERIC NOT NULL DEFAULT 0,
 counted_quantity NUMERIC NOT NULL DEFAULT 0,
 difference NUMERIC NOT NULL DEFAULT 0,
 FOREIGN KEY(stocktake_id) REFERENCES stocktakes(id) ON DELETE CASCADE,
 FOREIGN KEY(product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS stock_adjustments(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 warehouse_id INTEGER NOT NULL,
 status VARCHAR(50) NOT NULL DEFAULT 'draft',
 reason TEXT,
 created_by INTEGER,
 approved_by INTEGER,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(warehouse_id) REFERENCES warehouses(id)
);

CREATE INDEX IF NOT EXISTS idx_stock_product ON stock_balances(product_id);
CREATE INDEX IF NOT EXISTS idx_movements_product ON stock_movements(product_id);
CREATE INDEX IF NOT EXISTS idx_movements_date ON stock_movements(created_at);
""")

branch=c.execute("SELECT id FROM branches WHERE code='MAIN' LIMIT 1").fetchone()
if not branch:
    raise RuntimeError("الفرع الرئيسي غير موجود")

c.execute("""
INSERT OR IGNORE INTO warehouses(branch_id,name,code,warehouse_type)
VALUES(?,?,?,'main')
""",(branch[0],"المستودع الرئيسي","MAIN-WH"))

c.commit()

required=["warehouses","warehouse_zones","warehouse_aisles","warehouse_shelves","warehouse_bins","product_locations","stock_balances","stock_movements","stocktakes","stocktake_items","stock_adjustments"]
existing={x[0] for x in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
missing=[x for x in required if x not in existing]
if missing: raise RuntimeError("جداول ناقصة: "+",".join(missing))
if c.execute("PRAGMA integrity_check").fetchone()[0]!="ok": raise RuntimeError("فشل integrity_check")

c.close()

sf=ROOT/".lulu_state"/"build_state.json"
state=json.loads(sf.read_text(encoding="utf-8"))
state["last_completed_stage"]=4
state["last_completed_at"]=datetime.now().isoformat()
sf.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding="utf-8")

print("WAREHOUSES: OK")
print("LOCATIONS: OK")
print("STOCK BALANCES: OK")
print("STOCK MOVEMENTS: OK")
print("STOCKTAKES: OK")
print("INTEGRITY: OK")
print("STATE: UPDATED")
print("STATUS: SUCCESS")
