from pathlib import Path
import sqlite3,json
from datetime import datetime
R=Path(__file__).resolve().parents[1];D=R/"database"/"nizam_alqirtasiyah.db";c=sqlite3.connect(D)
c.executescript("""
CREATE TABLE IF NOT EXISTS report_definitions(id INTEGER PRIMARY KEY AUTOINCREMENT,code TEXT UNIQUE NOT NULL,name TEXT NOT NULL,category TEXT,query_sql TEXT,format TEXT DEFAULT 'pdf',is_active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS report_runs(id INTEGER PRIMARY KEY AUTOINCREMENT,report_id INTEGER NOT NULL,parameters TEXT,output_path TEXT,status TEXT DEFAULT 'completed',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS dashboard_widgets(id INTEGER PRIMARY KEY AUTOINCREMENT,code TEXT UNIQUE NOT NULL,title TEXT NOT NULL,widget_type TEXT,configuration TEXT,is_active INTEGER DEFAULT 1);
""")
reports=[("SALES_DAILY","المبيعات اليومية","المبيعات"),("SALES_SUMMARY","ملخص المبيعات","المبيعات"),("PURCHASES","تقرير المشتريات","المشتريات"),("INVENTORY","تقرير المخزون","المخزون"),("CUSTOMERS_BALANCE","أرصدة العملاء","العملاء"),("SUPPLIERS_BALANCE","أرصدة الموردين","الموردون"),("TRIAL_BALANCE","ميزان المراجعة","المحاسبة"),("INCOME_STATEMENT","قائمة الدخل","المحاسبة"),("BALANCE_SHEET","الميزانية","المحاسبة"),("CASH_FLOW","التدفقات النقدية","المحاسبة")]
for x in reports:c.execute("INSERT OR IGNORE INTO report_definitions(code,name,category) VALUES(?,?,?)",x)
if c.execute("PRAGMA integrity_check").fetchone()[0]!="ok":raise RuntimeError("فشل integrity_check")
c.commit();c.close();sf=R/".lulu_state"/"build_state.json";st=json.loads(sf.read_text(encoding="utf-8"))
if st.get("last_completed_stage",0)<18:raise RuntimeError("المرحلة 18 غير مكتملة")
st["last_completed_stage"]=19;st["last_completed_at"]=datetime.now().isoformat();sf.write_text(json.dumps(st,ensure_ascii=False,indent=2),encoding="utf-8")
print("REPORT DEFINITIONS: OK");print("FINANCIAL REPORTS: OK");print("REPORT RUNS: OK");print("STATUS: SUCCESS")
