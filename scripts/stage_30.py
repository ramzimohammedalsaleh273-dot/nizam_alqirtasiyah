from pathlib import Path
import sqlite3,json,sys
from datetime import datetime
R=Path(__file__).resolve().parents[1];D=R/"database"/"nizam_alqirtasiyah.db"
c=sqlite3.connect(D)
required=[
"companies","branches","users","roles","permissions","products","customers",
"suppliers","sales","sale_items","purchase_orders","cash_registers",
"accounts","journal_entries","tax_invoices","printing_orders","employees",
"payroll_runs","assets","contracts","report_definitions","analytics_metrics",
"notifications","sync_queue","integrations","workflows","backup_jobs",
"application_versions","search_index"
]
existing={x[0] for x in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
missing=[x for x in required if x not in existing]
if missing:
 print("MISSING_TABLES:",",".join(missing));c.close();sys.exit(1)
if c.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
 c.close();raise RuntimeError("فشل integrity_check")
c.close()
sf=R/".lulu_state"/"build_state.json";st=json.loads(sf.read_text(encoding="utf-8"))
if st.get("last_completed_stage",0)<29:raise RuntimeError("المرحلة 29 غير مكتملة")
st["last_completed_stage"]=30;st["last_completed_at"]=datetime.now().isoformat();st["tests_stage_30"]="PASSED"
sf.write_text(json.dumps(st,ensure_ascii=False,indent=2),encoding="utf-8")
print("DATABASE STRUCTURE: PASSED")
print("REQUIRED MODULE TABLES: PASSED")
print("SQLITE INTEGRITY: PASSED")
print("STATE: UPDATED")
print("STATUS: SUCCESS")
