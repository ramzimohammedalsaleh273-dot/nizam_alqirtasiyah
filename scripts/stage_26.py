from pathlib import Path
import sqlite3,json
from datetime import datetime
R=Path(__file__).resolve().parents[1];D=R/"database"/"nizam_alqirtasiyah.db";c=sqlite3.connect(D)
c.executescript("""
CREATE TABLE IF NOT EXISTS backup_jobs(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 backup_type TEXT NOT NULL,
 destination TEXT,
 status TEXT DEFAULT 'completed',
 started_at TEXT DEFAULT CURRENT_TIMESTAMP,
 completed_at TEXT,
 file_size INTEGER,
 checksum TEXT
);
CREATE TABLE IF NOT EXISTS restore_jobs(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 backup_file TEXT NOT NULL,
 status TEXT DEFAULT 'pending',
 started_at TEXT DEFAULT CURRENT_TIMESTAMP,
 completed_at TEXT,
 message TEXT
);
CREATE TABLE IF NOT EXISTS backup_settings(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 setting_key TEXT UNIQUE NOT NULL,
 setting_value TEXT
);
""")
for x in [("auto_backup_enabled","1"),("backup_frequency","daily"),("keep_copies","30"),("verify_backup","1")]:
 c.execute("INSERT OR IGNORE INTO backup_settings(setting_key,setting_value) VALUES(?,?)",x)
if c.execute("PRAGMA integrity_check").fetchone()[0]!="ok":raise RuntimeError("فشل integrity_check")
c.commit();c.close();sf=R/".lulu_state"/"build_state.json";st=json.loads(sf.read_text(encoding="utf-8"))
if st.get("last_completed_stage",0)<25:raise RuntimeError("المرحلة 25 غير مكتملة")
st["last_completed_stage"]=26;st["last_completed_at"]=datetime.now().isoformat();sf.write_text(json.dumps(st,ensure_ascii=False,indent=2),encoding="utf-8")
print("BACKUP SYSTEM: OK");print("RESTORE SYSTEM: OK");print("BACKUP SETTINGS: OK");print("STATUS: SUCCESS")
