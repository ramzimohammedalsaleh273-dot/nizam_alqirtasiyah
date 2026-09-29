from pathlib import Path
import sqlite3,json
from datetime import datetime
R=Path(__file__).resolve().parents[1]; D=R/"database"/"nizam_alqirtasiyah.db"
c=sqlite3.connect(D)
c.executescript("""
CREATE TABLE IF NOT EXISTS accounting_event_rules(
 id INTEGER PRIMARY KEY AUTOINCREMENT,event_code TEXT UNIQUE NOT NULL,event_name TEXT NOT NULL,debit_account TEXT,credit_account TEXT,is_active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS accounting_links(
 id INTEGER PRIMARY KEY AUTOINCREMENT,event_code TEXT NOT NULL,source_type TEXT NOT NULL,source_id INTEGER,debit_account TEXT,credit_account TEXT,amount REAL DEFAULT 0,status TEXT DEFAULT 'pending',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS posting_batches(
 id INTEGER PRIMARY KEY AUTOINCREMENT,batch_no TEXT UNIQUE NOT NULL,source_type TEXT,source_id INTEGER,status TEXT DEFAULT 'posted',posted_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_accounting_links_event ON accounting_links(event_code);
""")
rules=[
("SALE","بيع","4100","1100"),("SALE_CREDIT","بيع آجل","1300","4100"),
("PURCHASE","شراء","1400","2100"),("PURCHASE_PAYMENT","سداد مورد","2100","1100"),
("CUSTOMER_PAYMENT","تحصيل عميل","1100","1300"),("EXPENSE","مصروف","5100","1100"),
("SALE_RETURN","مرتجع مبيعات","4100","1100"),("PURCHASE_RETURN","مرتجع مشتريات","2100","1400")]
for x in rules:c.execute("INSERT OR IGNORE INTO accounting_event_rules(event_code,event_name,debit_account,credit_account) VALUES(?,?,?,?)",x)
c.commit()
req=["accounting_event_rules","accounting_links","posting_batches"]
ex={x[0] for x in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
if any(x not in ex for x in req): raise RuntimeError("جداول المرحلة 11 ناقصة")
if c.execute("PRAGMA integrity_check").fetchone()[0]!="ok": raise RuntimeError("فشل فحص قاعدة البيانات")
c.close()
sf=R/".lulu_state"/"build_state.json"; st=json.loads(sf.read_text(encoding="utf-8")); 
if st.get("last_completed_stage",0)<10: raise RuntimeError("المرحلة 10 غير مكتملة")
st["last_completed_stage"]=11;st["last_completed_at"]=datetime.now().isoformat();sf.write_text(json.dumps(st,ensure_ascii=False,indent=2),encoding="utf-8")
print("ACCOUNTING AUTO-LINKS: OK");print("POSTING RULES: OK");print("INTEGRITY: OK");print("STATE: UPDATED");print("STATUS: SUCCESS")
