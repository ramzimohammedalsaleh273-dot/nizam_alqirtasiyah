from pathlib import Path
import sqlite3,json
from datetime import datetime

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/"database"/"nizam_alqirtasiyah.db"
c=sqlite3.connect(DB)
c.execute("PRAGMA foreign_keys=ON")

c.executescript("""
CREATE TABLE IF NOT EXISTS product_categories(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 parent_id INTEGER,
 name VARCHAR(200) NOT NULL,
 code VARCHAR(100) UNIQUE,
 description TEXT,
 is_active INTEGER NOT NULL DEFAULT 1,
 FOREIGN KEY(parent_id) REFERENCES product_categories(id)
);

CREATE TABLE IF NOT EXISTS brands(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name VARCHAR(200) NOT NULL UNIQUE,
 description TEXT,
 is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS products(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 sku VARCHAR(100) NOT NULL UNIQUE,
 name_ar VARCHAR(300) NOT NULL,
 name_en VARCHAR(300),
 category_id INTEGER,
 brand_id INTEGER,
 unit_id INTEGER,
 product_type VARCHAR(30) NOT NULL DEFAULT 'inventory',
 description TEXT,
 cost_price NUMERIC NOT NULL DEFAULT 0,
 sale_price NUMERIC NOT NULL DEFAULT 0,
 wholesale_price NUMERIC NOT NULL DEFAULT 0,
 school_price NUMERIC NOT NULL DEFAULT 0,
 corporate_price NUMERIC NOT NULL DEFAULT 0,
 min_price NUMERIC NOT NULL DEFAULT 0,
 reorder_point NUMERIC NOT NULL DEFAULT 0,
 min_stock NUMERIC NOT NULL DEFAULT 0,
 max_stock NUMERIC NOT NULL DEFAULT 0,
 is_active INTEGER NOT NULL DEFAULT 1,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(category_id) REFERENCES product_categories(id),
 FOREIGN KEY(brand_id) REFERENCES brands(id),
 FOREIGN KEY(unit_id) REFERENCES units(id)
);

CREATE TABLE IF NOT EXISTS product_barcodes(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 product_id INTEGER NOT NULL,
 barcode VARCHAR(100) NOT NULL UNIQUE,
 is_primary INTEGER NOT NULL DEFAULT 0,
 FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS product_prices(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 product_id INTEGER NOT NULL,
 price_type VARCHAR(50) NOT NULL,
 price NUMERIC NOT NULL DEFAULT 0,
 min_quantity NUMERIC NOT NULL DEFAULT 1,
 start_date TEXT,
 end_date TEXT,
 is_active INTEGER NOT NULL DEFAULT 1,
 UNIQUE(product_id,price_type,min_quantity),
 FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS product_units(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 product_id INTEGER NOT NULL,
 unit_id INTEGER NOT NULL,
 conversion_factor NUMERIC NOT NULL DEFAULT 1,
 is_base INTEGER NOT NULL DEFAULT 0,
 UNIQUE(product_id,unit_id),
 FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE,
 FOREIGN KEY(unit_id) REFERENCES units(id)
);

CREATE TABLE IF NOT EXISTS product_images(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 product_id INTEGER NOT NULL,
 file_path TEXT NOT NULL,
 is_primary INTEGER NOT NULL DEFAULT 0,
 FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS product_supplier_links(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 product_id INTEGER NOT NULL,
 supplier_id INTEGER,
 supplier_sku VARCHAR(100),
 purchase_price NUMERIC NOT NULL DEFAULT 0,
 lead_time_days INTEGER DEFAULT 0,
 is_preferred INTEGER NOT NULL DEFAULT 0,
 UNIQUE(product_id,supplier_id),
 FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_products_name ON products(name_ar);
CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku);
CREATE INDEX IF NOT EXISTS idx_barcodes_barcode ON product_barcodes(barcode);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id);
""")

categories=[
("أدوات الكتابة","WRITING"),
("القرطاسية","STATIONERY"),
("الفنون","ART"),
("المدرسة","SCHOOL"),
("الطباعة","PRINTING"),
("التقنية","TECH")
]

for n,code in categories:
    c.execute("INSERT OR IGNORE INTO product_categories(name,code) VALUES (?,?)",(n,code))

for name in ["Pilot","BIC","Faber-Castell","Staedtler","Maped"]:
    c.execute("INSERT OR IGNORE INTO brands(name) VALUES (?)",(name,))

c.commit()

required=["product_categories","brands","products","product_barcodes","product_prices","product_units","product_images","product_supplier_links"]
existing={x[0] for x in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
missing=[x for x in required if x not in existing]
if missing: raise RuntimeError("جداول ناقصة: "+",".join(missing))
if c.execute("PRAGMA integrity_check").fetchone()[0]!="ok": raise RuntimeError("فشل فحص قاعدة البيانات")

c.close()

state_file=ROOT/".lulu_state"/"build_state.json"
state=json.loads(state_file.read_text(encoding="utf-8"))
state["last_completed_stage"]=3
state["last_completed_at"]=datetime.now().isoformat()
state_file.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding="utf-8")

print("PRODUCT TABLES: OK")
print("CATEGORIES: OK")
print("BRANDS: OK")
print("PRICING STRUCTURE: OK")
print("INTEGRITY: OK")
print("STATE: UPDATED")
print("STATUS: SUCCESS")
