from pathlib import Path
import sqlite3,json
from datetime import datetime
R=Path(__file__).resolve().parents[1];D=R/"database"/"nizam_alqirtasiyah.db";c=sqlite3.connect(D)
c.executescript("""
CREATE TABLE IF NOT EXISTS payroll_periods(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT UNIQUE NOT NULL,start_date TEXT,end_date TEXT,status TEXT DEFAULT 'open');
CREATE TABLE IF NOT EXISTS payroll_runs(id INTEGER PRIMARY KEY AUTOINCREMENT,period_id INTEGER NOT NULL,run_no TEXT UNIQUE NOT NULL,status TEXT DEFAULT 'draft',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS payroll_items(id INTEGER PRIMARY KEY AUTOINCREMENT,run_id INTEGER NOT NULL,employee_id INTEGER NOT NULL,basic_salary REAL DEFAULT 0,allowances REAL DEFAULT 0,overtime REAL DEFAULT 0,deductions REAL DEFAULT 0,tax REAL DEFAULT 0,net_salary REAL DEFAULT 0);
CREATE TABLE IF NOT EXISTS salary_components(id INTEGER PRIMARY KEY AUTOINCREMENT,code TEXT UNIQUE NOT NULL,name TEXT NOT NULL,component_type TEXT NOT NULL,is_active INTEGER DEFAULT 1);
""")
for x in [("BASIC","الراتب الأساسي","earning"),("ALLOWANCE","البدلات","earning"),("OVERTIME","الإضافي","earning"),("DEDUCTION","الخصومات","deduction")]:c.execute("INSERT OR IGNORE INTO salary_components(code,name,component_type) VALUES(?,?,?)",x)
if c.execute("PRAGMA integrity_check").fetchone()[0]!="ok":raise RuntimeError("فشل integrity_check")
c.commit();c.close();sf=R/".lulu_state"/"build_state.json";st=json.loads(sf.read_text(encoding="utf-8"))
if st.get("last_completed_stage",0)<15:raise RuntimeError("المرحلة 15 غير مكتملة")
st["last_completed_stage"]=16;st["last_completed_at"]=datetime.now().isoformat();sf.write_text(json.dumps(st,ensure_ascii=False,indent=2),encoding="utf-8")
print("PAYROLL: OK");print("SALARY COMPONENTS: OK");print("PAYROLL ITEMS: OK");print("STATUS: SUCCESS")
