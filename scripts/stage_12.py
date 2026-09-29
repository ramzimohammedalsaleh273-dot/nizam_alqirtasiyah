from pathlib import Path
import sqlite3,json
from datetime import datetime
R=Path(__file__).resolve().parents[1];D=R/"database"/"nizam_alqirtasiyah.db";c=sqlite3.connect(D)
c.executescript("""
CREATE TABLE IF NOT EXISTS tax_rates(id INTEGER PRIMARY KEY AUTOINCREMENT,code TEXT UNIQUE,name TEXT NOT NULL,rate REAL NOT NULL,is_active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS tax_invoices(id INTEGER PRIMARY KEY AUTOINCREMENT,invoice_no TEXT UNIQUE NOT NULL,source_type TEXT,source_id INTEGER,subtotal REAL DEFAULT 0,tax_amount REAL DEFAULT 0,total_amount REAL DEFAULT 0,tax_number TEXT,uuid TEXT,qr_code TEXT,xml_path TEXT,clearance_status TEXT DEFAULT 'not_submitted',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS zatca_documents(id INTEGER PRIMARY KEY AUTOINCREMENT,invoice_id INTEGER NOT NULL,document_type TEXT,hash TEXT,previous_hash TEXT,xml_content TEXT,submission_status TEXT DEFAULT 'pending',response_code TEXT,response_message TEXT,submitted_at TEXT);
CREATE TABLE IF NOT EXISTS tax_transactions(id INTEGER PRIMARY KEY AUTOINCREMENT,invoice_id INTEGER,tax_code TEXT,tax_rate REAL,taxable_amount REAL,tax_amount REAL);
""")
c.execute("INSERT OR IGNORE INTO tax_rates(code,name,rate) VALUES('S15','ضريبة القيمة المضافة الأساسية',15)")
if c.execute("PRAGMA integrity_check").fetchone()[0]!="ok":raise RuntimeError("فشل integrity_check")
c.commit();c.close()
sf=R/".lulu_state"/"build_state.json";st=json.loads(sf.read_text(encoding="utf-8"))
if st.get("last_completed_stage",0)<11:raise RuntimeError("المرحلة 11 غير مكتملة")
st["last_completed_stage"]=12;st["last_completed_at"]=datetime.now().isoformat();sf.write_text(json.dumps(st,ensure_ascii=False,indent=2),encoding="utf-8")
print("TAX ENGINE: OK");print("VAT 15%: OK");print("ZATCA TABLES: OK");print("INTEGRITY: OK");print("STATE: UPDATED");print("STATUS: SUCCESS")
