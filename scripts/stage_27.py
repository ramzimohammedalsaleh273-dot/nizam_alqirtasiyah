from pathlib import Path
import sqlite3,json
from datetime import datetime
R=Path(__file__).resolve().parents[1];D=R/"database"/"nizam_alqirtasiyah.db";c=sqlite3.connect(D)
c.executescript("""
CREATE TABLE IF NOT EXISTS application_versions(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 version TEXT UNIQUE NOT NULL,
 release_name TEXT,
 release_date TEXT,
 status TEXT DEFAULT 'installed'
);
CREATE TABLE IF NOT EXISTS update_packages(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 version TEXT NOT NULL,
 package_path TEXT,
 checksum TEXT,
 status TEXT DEFAULT 'available',
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS update_history(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 from_version TEXT,
 to_version TEXT,
 action TEXT,
 status TEXT,
 message TEXT,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS rollback_points(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 version TEXT,
 database_backup TEXT,
 application_backup TEXT,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
""")
c.execute("INSERT OR IGNORE INTO application_versions(version,release_name,release_date,status) VALUES('0.1.0','قاعدة النظام','2026-09-22','development')")
if c.execute("PRAGMA integrity_check").fetchone()[0]!="ok":raise RuntimeError("فشل integrity_check")
c.commit();c.close();sf=R/".lulu_state"/"build_state.json";st=json.loads(sf.read_text(encoding="utf-8"))
if st.get("last_completed_stage",0)<26:raise RuntimeError("المرحلة 26 غير مكتملة")
st["last_completed_stage"]=27;st["last_completed_at"]=datetime.now().isoformat();sf.write_text(json.dumps(st,ensure_ascii=False,indent=2),encoding="utf-8")
print("VERSIONING: OK");print("UPDATE SYSTEM: OK");print("ROLLBACK POINTS: OK");print("STATUS: SUCCESS")
