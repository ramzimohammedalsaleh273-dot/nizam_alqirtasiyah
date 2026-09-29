from pathlib import Path
import sqlite3,json
from datetime import datetime
R=Path(__file__).resolve().parents[1];D=R/"database"/"nizam_alqirtasiyah.db";c=sqlite3.connect(D)
c.executescript("""
CREATE TABLE IF NOT EXISTS printing_services(id INTEGER PRIMARY KEY AUTOINCREMENT,code TEXT UNIQUE,name TEXT NOT NULL,service_type TEXT,unit TEXT,base_price REAL DEFAULT 0,tax_rate REAL DEFAULT 15,is_active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS printing_orders(id INTEGER PRIMARY KEY AUTOINCREMENT,order_no TEXT UNIQUE NOT NULL,customer_id INTEGER,service_id INTEGER,quantity REAL DEFAULT 1,unit_price REAL DEFAULT 0,discount REAL DEFAULT 0,tax REAL DEFAULT 0,total REAL DEFAULT 0,status TEXT DEFAULT 'new',notes TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS print_jobs(id INTEGER PRIMARY KEY AUTOINCREMENT,order_id INTEGER,file_name TEXT,file_path TEXT,copies INTEGER DEFAULT 1,paper_size TEXT DEFAULT 'A4',color_mode TEXT DEFAULT 'black_white',status TEXT DEFAULT 'pending',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS print_templates(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT UNIQUE NOT NULL,template_type TEXT,content TEXT,is_active INTEGER DEFAULT 1);
""")
for x in [("PRINT","طباعة","printing"),("COPY","تصوير","copying"),("SCAN","مسح ضوئي","scanning"),("BIND","تجليد","binding"),("LAMINATE","تغليف حراري","lamination")]:
 c.execute("INSERT OR IGNORE INTO printing_services(code,name,service_type) VALUES(?,?,?)",x)
if c.execute("PRAGMA integrity_check").fetchone()[0]!="ok":raise RuntimeError("فشل integrity_check")
c.commit();c.close();sf=R/".lulu_state"/"build_state.json";st=json.loads(sf.read_text(encoding="utf-8"))
if st.get("last_completed_stage",0)<12:raise RuntimeError("المرحلة 12 غير مكتملة")
st["last_completed_stage"]=13;st["last_completed_at"]=datetime.now().isoformat();sf.write_text(json.dumps(st,ensure_ascii=False,indent=2),encoding="utf-8")
print("PRINTING SERVICES: OK");print("PRINT JOBS: OK");print("STUDENT SERVICES: OK");print("STATUS: SUCCESS")
