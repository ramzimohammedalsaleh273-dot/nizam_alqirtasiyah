from pathlib import Path
import sqlite3,json
from datetime import datetime
R=Path(__file__).resolve().parents[1];D=R/"database"/"nizam_alqirtasiyah.db";c=sqlite3.connect(D)
c.executescript("""
CREATE TABLE IF NOT EXISTS contract_types(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT UNIQUE NOT NULL);
CREATE TABLE IF NOT EXISTS contracts(id INTEGER PRIMARY KEY AUTOINCREMENT,contract_no TEXT UNIQUE NOT NULL,title TEXT NOT NULL,contract_type_id INTEGER,party_type TEXT,party_id INTEGER,start_date TEXT,end_date TEXT,value REAL DEFAULT 0,status TEXT DEFAULT 'draft',terms TEXT);
CREATE TABLE IF NOT EXISTS contract_payments(id INTEGER PRIMARY KEY AUTOINCREMENT,contract_id INTEGER NOT NULL,due_date TEXT,amount REAL DEFAULT 0,status TEXT DEFAULT 'pending',paid_at TEXT);
CREATE TABLE IF NOT EXISTS contract_documents(id INTEGER PRIMARY KEY AUTOINCREMENT,contract_id INTEGER NOT NULL,document_id INTEGER NOT NULL);
""")
for x in ["مورد","عميل","موظف","إيجار","خدمة"]:c.execute("INSERT OR IGNORE INTO contract_types(name) VALUES(?)",(x,))
if c.execute("PRAGMA integrity_check").fetchone()[0]!="ok":raise RuntimeError("فشل integrity_check")
c.commit();c.close();sf=R/".lulu_state"/"build_state.json";st=json.loads(sf.read_text(encoding="utf-8"))
if st.get("last_completed_stage",0)<17:raise RuntimeError("المرحلة 17 غير مكتملة")
st["last_completed_stage"]=18;st["last_completed_at"]=datetime.now().isoformat();sf.write_text(json.dumps(st,ensure_ascii=False,indent=2),encoding="utf-8")
print("CONTRACTS: OK");print("CONTRACT PAYMENTS: OK");print("CONTRACT DOCUMENTS: OK");print("STATUS: SUCCESS")
