from pathlib import Path
import sqlite3,json
from datetime import datetime
R=Path(__file__).resolve().parents[1];D=R/"database"/"nizam_alqirtasiyah.db";c=sqlite3.connect(D)
c.executescript("""
CREATE TABLE IF NOT EXISTS departments(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT UNIQUE NOT NULL,is_active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS job_positions(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT UNIQUE NOT NULL,department_id INTEGER,base_salary REAL DEFAULT 0,is_active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS employees(id INTEGER PRIMARY KEY AUTOINCREMENT,employee_no TEXT UNIQUE NOT NULL,full_name TEXT NOT NULL,phone TEXT,email TEXT,department_id INTEGER,position_id INTEGER,hire_date TEXT,status TEXT DEFAULT 'active',basic_salary REAL DEFAULT 0);
CREATE TABLE IF NOT EXISTS employee_attendance(id INTEGER PRIMARY KEY AUTOINCREMENT,employee_id INTEGER NOT NULL,attendance_date TEXT NOT NULL,check_in TEXT,check_out TEXT,status TEXT DEFAULT 'present',notes TEXT,UNIQUE(employee_id,attendance_date));
CREATE TABLE IF NOT EXISTS employee_leaves(id INTEGER PRIMARY KEY AUTOINCREMENT,employee_id INTEGER NOT NULL,leave_type TEXT,start_date TEXT,end_date TEXT,status TEXT DEFAULT 'pending',reason TEXT);
""")
for x in ["الإدارة","المحاسبة","المبيعات","المخزون","المشتريات","الطباعة","الموارد البشرية"]:c.execute("INSERT OR IGNORE INTO departments(name) VALUES(?)",(x,))
if c.execute("PRAGMA integrity_check").fetchone()[0]!="ok":raise RuntimeError("فشل integrity_check")
c.commit();c.close();sf=R/".lulu_state"/"build_state.json";st=json.loads(sf.read_text(encoding="utf-8"))
if st.get("last_completed_stage",0)<14:raise RuntimeError("المرحلة 14 غير مكتملة")
st["last_completed_stage"]=15;st["last_completed_at"]=datetime.now().isoformat();sf.write_text(json.dumps(st,ensure_ascii=False,indent=2),encoding="utf-8")
print("HR: OK");print("EMPLOYEES: OK");print("ATTENDANCE: OK");print("LEAVES: OK");print("STATUS: SUCCESS")
