from pathlib import Path
import sqlite3,json
from datetime import datetime
R=Path(__file__).resolve().parents[1];D=R/"database"/"nizam_alqirtasiyah.db";c=sqlite3.connect(D)
c.executescript("""
CREATE TABLE IF NOT EXISTS search_index(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 entity_type TEXT NOT NULL,
 entity_id INTEGER NOT NULL,
 search_text TEXT NOT NULL,
 updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_search_text ON search_index(search_text);
CREATE TABLE IF NOT EXISTS quick_actions(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 code TEXT UNIQUE NOT NULL,
 name TEXT NOT NULL,
 route TEXT,
 required_permission TEXT,
 is_active INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS operation_center_tasks(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 task_type TEXT,
 title TEXT NOT NULL,
 entity_type TEXT,
 entity_id INTEGER,
 priority TEXT DEFAULT 'normal',
 status TEXT DEFAULT 'open',
 assigned_user_id INTEGER,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
""")
for x in [("NEW_SALE","فاتورة بيع جديدة","sales"),("NEW_PURCHASE","شراء جديد","purchases"),("STOCKTAKE","جرد المخزون","inventory"),("CUSTOMER_PAYMENT","تحصيل عميل","customers"),("SUPPLIER_PAYMENT","سداد مورد","suppliers")]:
 c.execute("INSERT OR IGNORE INTO quick_actions(code,name,route) VALUES(?,?,?)",x)
if c.execute("PRAGMA integrity_check").fetchone()[0]!="ok":raise RuntimeError("فشل integrity_check")
c.commit();c.close();sf=R/".lulu_state"/"build_state.json";st=json.loads(sf.read_text(encoding="utf-8"))
if st.get("last_completed_stage",0)<27:raise RuntimeError("المرحلة 27 غير مكتملة")
st["last_completed_stage"]=28;st["last_completed_at"]=datetime.now().isoformat();sf.write_text(json.dumps(st,ensure_ascii=False,indent=2),encoding="utf-8")
print("GLOBAL SEARCH: OK");print("QUICK ACTIONS: OK");print("OPERATION CENTER: OK");print("STATUS: SUCCESS")
