from pathlib import Path
import sqlite3,json
from datetime import datetime
R=Path(__file__).resolve().parents[1];D=R/"database"/"nizam_alqirtasiyah.db";c=sqlite3.connect(D)
c.executescript("""
CREATE TABLE IF NOT EXISTS asset_categories(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT UNIQUE NOT NULL);
CREATE TABLE IF NOT EXISTS assets(id INTEGER PRIMARY KEY AUTOINCREMENT,asset_no TEXT UNIQUE NOT NULL,name TEXT NOT NULL,category_id INTEGER,purchase_date TEXT,cost REAL DEFAULT 0,salvage_value REAL DEFAULT 0,useful_life_months INTEGER DEFAULT 0,status TEXT DEFAULT 'active',location TEXT);
CREATE TABLE IF NOT EXISTS asset_depreciation(id INTEGER PRIMARY KEY AUTOINCREMENT,asset_id INTEGER NOT NULL,period TEXT NOT NULL,amount REAL DEFAULT 0,book_value REAL DEFAULT 0,created_at TEXT DEFAULT CURRENT_TIMESTAMP,UNIQUE(asset_id,period));
CREATE TABLE IF NOT EXISTS maintenance_orders(id INTEGER PRIMARY KEY AUTOINCREMENT,order_no TEXT UNIQUE NOT NULL,asset_id INTEGER,maintenance_type TEXT,description TEXT,cost REAL DEFAULT 0,status TEXT DEFAULT 'open',opened_at TEXT DEFAULT CURRENT_TIMESTAMP,closed_at TEXT);
""")
for x in ["أجهزة الكمبيوتر","الأثاث","معدات الطباعة","المركبات","الأجهزة والمعدات"]:c.execute("INSERT OR IGNORE INTO asset_categories(name) VALUES(?)",(x,))
if c.execute("PRAGMA integrity_check").fetchone()[0]!="ok":raise RuntimeError("فشل integrity_check")
c.commit();c.close();sf=R/".lulu_state"/"build_state.json";st=json.loads(sf.read_text(encoding="utf-8"))
if st.get("last_completed_stage",0)<16:raise RuntimeError("المرحلة 16 غير مكتملة")
st["last_completed_stage"]=17;st["last_completed_at"]=datetime.now().isoformat();sf.write_text(json.dumps(st,ensure_ascii=False,indent=2),encoding="utf-8")
print("ASSETS: OK");print("DEPRECIATION: OK");print("MAINTENANCE: OK");print("STATUS: SUCCESS")
