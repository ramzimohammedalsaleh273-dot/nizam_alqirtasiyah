from pathlib import Path
import sqlite3,json
from datetime import datetime
R=Path(__file__).resolve().parents[1];D=R/"database"/"nizam_alqirtasiyah.db";c=sqlite3.connect(D)
c.executescript("""
CREATE TABLE IF NOT EXISTS branch_settings(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 branch_id INTEGER NOT NULL,
 setting_key TEXT NOT NULL,
 setting_value TEXT,
 UNIQUE(branch_id,setting_key)
);
CREATE TABLE IF NOT EXISTS branch_sequences(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 branch_id INTEGER NOT NULL,
 sequence_type TEXT NOT NULL,
 prefix TEXT DEFAULT '',
 current_number INTEGER DEFAULT 0,
 UNIQUE(branch_id,sequence_type)
);
CREATE TABLE IF NOT EXISTS branch_users(
 branch_id INTEGER NOT NULL,
 user_id INTEGER NOT NULL,
 PRIMARY KEY(branch_id,user_id)
);
CREATE TABLE IF NOT EXISTS interbranch_transfers(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 transfer_no TEXT UNIQUE NOT NULL,
 from_branch_id INTEGER NOT NULL,
 to_branch_id INTEGER NOT NULL,
 status TEXT DEFAULT 'draft',
 notes TEXT,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
""")
if c.execute("PRAGMA integrity_check").fetchone()[0]!="ok":raise RuntimeError("فشل integrity_check")
c.commit();c.close();sf=R/".lulu_state"/"build_state.json";st=json.loads(sf.read_text(encoding="utf-8"))
if st.get("last_completed_stage",0)<23:raise RuntimeError("المرحلة 23 غير مكتملة")
st["last_completed_stage"]=24;st["last_completed_at"]=datetime.now().isoformat();sf.write_text(json.dumps(st,ensure_ascii=False,indent=2),encoding="utf-8")
print("MULTI-BRANCH: OK");print("BRANCH SETTINGS: OK");print("BRANCH USERS: OK");print("INTERBRANCH TRANSFERS: OK");print("STATUS: SUCCESS")
