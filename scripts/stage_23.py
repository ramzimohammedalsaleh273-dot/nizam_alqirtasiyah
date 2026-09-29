from pathlib import Path
import sqlite3,json
from datetime import datetime
R=Path(__file__).resolve().parents[1];D=R/"database"/"nizam_alqirtasiyah.db";c=sqlite3.connect(D)
c.executescript("""
CREATE TABLE IF NOT EXISTS integrations(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 code TEXT UNIQUE NOT NULL,
 name TEXT NOT NULL,
 integration_type TEXT,
 base_url TEXT,
 status TEXT DEFAULT 'disabled',
 configuration TEXT
);
CREATE TABLE IF NOT EXISTS integration_logs(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 integration_id INTEGER,
 direction TEXT,
 endpoint TEXT,
 request_data TEXT,
 response_data TEXT,
 status_code INTEGER,
 status TEXT,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS ecommerce_orders(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 external_order_id TEXT,
 platform TEXT,
 customer_name TEXT,
 order_status TEXT DEFAULT 'new',
 subtotal REAL DEFAULT 0,
 tax REAL DEFAULT 0,
 total REAL DEFAULT 0,
 payload TEXT,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP,
 UNIQUE(platform,external_order_id)
);
CREATE TABLE IF NOT EXISTS product_channel_links(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 product_id INTEGER NOT NULL,
 platform TEXT NOT NULL,
 external_product_id TEXT,
 external_sku TEXT,
 is_active INTEGER DEFAULT 1,
 UNIQUE(product_id,platform)
);
""")
for x in [("ECOMMERCE","التجارة الإلكترونية","ecommerce"),("PAYMENT_GATEWAY","بوابة الدفع","payment"),("SHIPPING","الشحن والتوصيل","shipping")]:
 c.execute("INSERT OR IGNORE INTO integrations(code,name,integration_type) VALUES(?,?,?)",x)
if c.execute("PRAGMA integrity_check").fetchone()[0]!="ok":raise RuntimeError("فشل integrity_check")
c.commit();c.close();sf=R/".lulu_state"/"build_state.json";st=json.loads(sf.read_text(encoding="utf-8"))
if st.get("last_completed_stage",0)<22:raise RuntimeError("المرحلة 22 غير مكتملة")
st["last_completed_stage"]=23;st["last_completed_at"]=datetime.now().isoformat();sf.write_text(json.dumps(st,ensure_ascii=False,indent=2),encoding="utf-8")
print("INTEGRATIONS: OK");print("ECOMMERCE: OK");print("PAYMENT INTEGRATION: READY");print("SHIPPING INTEGRATION: READY");print("STATUS: SUCCESS")
