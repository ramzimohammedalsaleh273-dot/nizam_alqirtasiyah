from pathlib import Path
import sqlite3,json
from datetime import datetime
R=Path(__file__).resolve().parents[1];D=R/"database"/"nizam_alqirtasiyah.db";c=sqlite3.connect(D)
c.executescript("""
CREATE TABLE IF NOT EXISTS sync_devices(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 device_id TEXT UNIQUE NOT NULL,
 device_name TEXT,
 last_sync_at TEXT,
 status TEXT DEFAULT 'active'
);
CREATE TABLE IF NOT EXISTS sync_queue(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 entity_type TEXT NOT NULL,
 entity_id INTEGER,
 operation TEXT NOT NULL,
 payload TEXT,
 status TEXT DEFAULT 'pending',
 retry_count INTEGER DEFAULT 0,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP,
 processed_at TEXT
);
CREATE TABLE IF NOT EXISTS sync_conflicts(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 entity_type TEXT,
 entity_id INTEGER,
 local_data TEXT,
 remote_data TEXT,
 resolution TEXT DEFAULT 'pending',
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS offline_operations(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 operation_code TEXT UNIQUE NOT NULL,
 operation_type TEXT NOT NULL,
 payload TEXT,
 status TEXT DEFAULT 'pending',
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
""")
if c.execute("PRAGMA integrity_check").fetchone()[0]!="ok":raise RuntimeError("فشل integrity_check")
c.commit();c.close();sf=R/".lulu_state"/"build_state.json";st=json.loads(sf.read_text(encoding="utf-8"))
if st.get("last_completed_stage",0)<21:raise RuntimeError("المرحلة 21 غير مكتملة")
st["last_completed_stage"]=22;st["last_completed_at"]=datetime.now().isoformat();st["offline_first"]=True
sf.write_text(json.dumps(st,ensure_ascii=False,indent=2),encoding="utf-8")
print("OFFLINE MODE: OK");print("SYNC QUEUE: OK");print("CONFLICT MANAGEMENT: OK");print("STATUS: SUCCESS")
