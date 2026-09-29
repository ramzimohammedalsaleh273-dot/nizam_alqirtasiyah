from pathlib import Path
import sqlite3,json
from datetime import datetime
R=Path(__file__).resolve().parents[1];D=R/"database"/"nizam_alqirtasiyah.db";c=sqlite3.connect(D)
c.executescript("""
CREATE TABLE IF NOT EXISTS documents(id INTEGER PRIMARY KEY AUTOINCREMENT,document_no TEXT UNIQUE NOT NULL,title TEXT NOT NULL,document_type TEXT,entity_type TEXT,entity_id INTEGER,file_name TEXT,file_path TEXT,mime_type TEXT,file_size INTEGER,description TEXT,created_by INTEGER,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS document_versions(id INTEGER PRIMARY KEY AUTOINCREMENT,document_id INTEGER NOT NULL,version_no INTEGER NOT NULL,file_path TEXT,file_hash TEXT,created_by INTEGER,created_at TEXT DEFAULT CURRENT_TIMESTAMP,UNIQUE(document_id,version_no));
CREATE TABLE IF NOT EXISTS document_links(id INTEGER PRIMARY KEY AUTOINCREMENT,document_id INTEGER NOT NULL,entity_type TEXT NOT NULL,entity_id INTEGER NOT NULL);
""")
if c.execute("PRAGMA integrity_check").fetchone()[0]!="ok":raise RuntimeError("فشل integrity_check")
c.commit();c.close();sf=R/".lulu_state"/"build_state.json";st=json.loads(sf.read_text(encoding="utf-8"))
if st.get("last_completed_stage",0)<13:raise RuntimeError("المرحلة 13 غير مكتملة")
st["last_completed_stage"]=14;st["last_completed_at"]=datetime.now().isoformat();sf.write_text(json.dumps(st,ensure_ascii=False,indent=2),encoding="utf-8")
print("DOCUMENTS: OK");print("DOCUMENT VERSIONS: OK");print("DOCUMENT LINKS: OK");print("STATUS: SUCCESS")
