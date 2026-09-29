from pathlib import Path
import sqlite3,json
from datetime import datetime
R=Path(__file__).resolve().parents[1];D=R/"database"/"nizam_alqirtasiyah.db";c=sqlite3.connect(D)
c.executescript("""
CREATE TABLE IF NOT EXISTS workflows(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 code TEXT UNIQUE NOT NULL,
 name TEXT NOT NULL,
 entity_type TEXT NOT NULL,
 is_active INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS workflow_steps(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 workflow_id INTEGER NOT NULL,
 step_no INTEGER NOT NULL,
 step_name TEXT NOT NULL,
 required_role_id INTEGER,
 UNIQUE(workflow_id,step_no)
);
CREATE TABLE IF NOT EXISTS approval_requests(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 request_no TEXT UNIQUE NOT NULL,
 workflow_id INTEGER NOT NULL,
 entity_type TEXT,
 entity_id INTEGER,
 requested_by INTEGER,
 current_step INTEGER DEFAULT 1,
 status TEXT DEFAULT 'pending',
 created_at TEXT DEFAULT CURRENT_TIMESTAMP,
 completed_at TEXT
);
CREATE TABLE IF NOT EXISTS approval_actions(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 request_id INTEGER NOT NULL,
 step_id INTEGER,
 user_id INTEGER,
 action TEXT NOT NULL,
 comment TEXT,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
""")
for x in [("PURCHASE_APPROVAL","اعتماد المشتريات","purchase"),("PAYMENT_APPROVAL","اعتماد المدفوعات","payment"),("DISCOUNT_APPROVAL","اعتماد الخصومات","discount"),("STOCK_ADJUSTMENT","اعتماد تعديل المخزون","stock_adjustment")]:
 c.execute("INSERT OR IGNORE INTO workflows(code,name,entity_type) VALUES(?,?,?)",x)
if c.execute("PRAGMA integrity_check").fetchone()[0]!="ok":raise RuntimeError("فشل integrity_check")
c.commit();c.close();sf=R/".lulu_state"/"build_state.json";st=json.loads(sf.read_text(encoding="utf-8"))
if st.get("last_completed_stage",0)<24:raise RuntimeError("المرحلة 24 غير مكتملة")
st["last_completed_stage"]=25;st["last_completed_at"]=datetime.now().isoformat();sf.write_text(json.dumps(st,ensure_ascii=False,indent=2),encoding="utf-8")
print("WORKFLOWS: OK");print("APPROVAL REQUESTS: OK");print("APPROVAL ACTIONS: OK");print("STATUS: SUCCESS")
