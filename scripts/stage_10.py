from pathlib import Path
import sqlite3,json
from datetime import datetime

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/"database"/"nizam_alqirtasiyah.db"
c=sqlite3.connect(DB)
c.execute("PRAGMA foreign_keys=ON")

c.executescript("""
CREATE TABLE IF NOT EXISTS account_types(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 code VARCHAR(50) NOT NULL UNIQUE,
 name VARCHAR(100) NOT NULL,
 normal_balance VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS chart_of_accounts(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 code VARCHAR(50) NOT NULL UNIQUE,
 name VARCHAR(250) NOT NULL,
 account_type_id INTEGER NOT NULL,
 parent_id INTEGER,
 level INTEGER NOT NULL DEFAULT 1,
 is_group INTEGER NOT NULL DEFAULT 0,
 is_active INTEGER NOT NULL DEFAULT 1,
 FOREIGN KEY(account_type_id) REFERENCES account_types(id),
 FOREIGN KEY(parent_id) REFERENCES chart_of_accounts(id)
);

CREATE TABLE IF NOT EXISTS cost_centers(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 code VARCHAR(50) NOT NULL UNIQUE,
 name VARCHAR(200) NOT NULL,
 parent_id INTEGER,
 is_active INTEGER NOT NULL DEFAULT 1,
 FOREIGN KEY(parent_id) REFERENCES cost_centers(id)
);

CREATE TABLE IF NOT EXISTS fiscal_years(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name VARCHAR(100) NOT NULL UNIQUE,
 start_date TEXT NOT NULL,
 end_date TEXT NOT NULL,
 status VARCHAR(30) NOT NULL DEFAULT 'open'
);

CREATE TABLE IF NOT EXISTS accounting_periods(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 fiscal_year_id INTEGER NOT NULL,
 name VARCHAR(100) NOT NULL,
 start_date TEXT NOT NULL,
 end_date TEXT NOT NULL,
 status VARCHAR(30) NOT NULL DEFAULT 'open',
 UNIQUE(fiscal_year_id,name),
 FOREIGN KEY(fiscal_year_id) REFERENCES fiscal_years(id)
);

CREATE TABLE IF NOT EXISTS journal_entries(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 entry_number VARCHAR(100) NOT NULL UNIQUE,
 entry_date TEXT NOT NULL,
 description TEXT,
 source_type VARCHAR(100),
 source_id INTEGER,
 status VARCHAR(30) NOT NULL DEFAULT 'posted',
 fiscal_period_id INTEGER,
 created_by INTEGER,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(fiscal_period_id) REFERENCES accounting_periods(id),
 FOREIGN KEY(created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS journal_entry_lines(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 journal_entry_id INTEGER NOT NULL,
 account_id INTEGER NOT NULL,
 cost_center_id INTEGER,
 description TEXT,
 debit NUMERIC NOT NULL DEFAULT 0,
 credit NUMERIC NOT NULL DEFAULT 0,
 FOREIGN KEY(journal_entry_id) REFERENCES journal_entries(id) ON DELETE CASCADE,
 FOREIGN KEY(account_id) REFERENCES chart_of_accounts(id),
 FOREIGN KEY(cost_center_id) REFERENCES cost_centers(id)
);

CREATE INDEX IF NOT EXISTS idx_accounts_code ON chart_of_accounts(code);
CREATE INDEX IF NOT EXISTS idx_journal_date ON journal_entries(entry_date);
CREATE INDEX IF NOT EXISTS idx_journal_source ON journal_entries(source_type,source_id);
CREATE INDEX IF NOT EXISTS idx_journal_lines_account ON journal_entry_lines(account_id);
""")

account_types=[
("asset","الأصول","debit"),
("liability","الخصوم","credit"),
("equity","حقوق الملكية","credit"),
("revenue","الإيرادات","credit"),
("expense","المصروفات","debit"),
("cogs","تكلفة المبيعات","debit")
]

for code,name,balance in account_types:
    c.execute("""
    INSERT OR IGNORE INTO account_types(code,name,normal_balance)
    VALUES(?,?,?)
    """,(code,name,balance))

types={r[0]:r[1] for r in c.execute("SELECT code,id FROM account_types")}

accounts=[
("1000","الأصول","asset",1),
("1100","النقدية","asset",0),
("1200","البنوك","asset",0),
("1300","العملاء","asset",0),
("1400","المخزون","asset",0),
("1500","الأصول الثابتة","asset",0),
("2000","الخصوم","liability",1),
("2100","الموردون","liability",0),
("2200","ضريبة القيمة المضافة","liability",0),
("3000","حقوق الملكية","equity",1),
("3100","رأس المال","equity",0),
("4000","الإيرادات","revenue",1),
("4100","مبيعات القرطاسية","revenue",0),
("4200","إيرادات الطباعة","revenue",0),
("5000","المصروفات وتكلفة المبيعات","expense",1),
("5100","تكلفة المبيعات","cogs",0),
("5200","مصروفات التشغيل","expense",0),
("5300","الرواتب","expense",0)
]

for code,name,typ,isgroup in accounts:
    parent_code=None
    if code=="1100": parent_code="1000"
    elif code=="1200": parent_code="1000"
    elif code=="1300": parent_code="1000"
    elif code=="1400": parent_code="1000"
    elif code=="1500": parent_code="1000"
    elif code=="2100": parent_code="2000"
    elif code=="2200": parent_code="2000"
    elif code=="3100": parent_code="3000"
    elif code=="4100": parent_code="4000"
    elif code=="4200": parent_code="4000"
    elif code in ("5100","5200","5300"): parent_code="5000"

    parent_id=None
    if parent_code:
        parent_id=c.execute(
            "SELECT id FROM chart_of_accounts WHERE code=?",
            (parent_code,)
        ).fetchone()
        parent_id=parent_id[0] if parent_id else None

    c.execute("""
    INSERT OR IGNORE INTO chart_of_accounts
    (code,name,account_type_id,parent_id,level,is_group)
    VALUES(?,?,?,?,?,?)
    """,(code,name,types[typ],parent_id,1 if not parent_code else 2,isgroup))

c.execute("""
INSERT OR IGNORE INTO cost_centers(code,name)
VALUES('MAIN','الفرع الرئيسي')
""")

c.execute("""
INSERT OR IGNORE INTO fiscal_years
(name,start_date,end_date,status)
VALUES('2026','2026-01-01','2026-12-31','open')
""")

fy=c.execute(
"SELECT id FROM fiscal_years WHERE name='2026'"
).fetchone()[0]

c.execute("""
INSERT OR IGNORE INTO accounting_periods
(fiscal_year_id,name,start_date,end_date,status)
VALUES(?,?,?,?,?)
""",(fy,"يناير 2026","2026-01-01","2026-01-31","open"))

c.commit()

required=[
"account_types","chart_of_accounts","cost_centers",
"fiscal_years","accounting_periods",
"journal_entries","journal_entry_lines"
]

existing={x[0] for x in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
missing=[x for x in required if x not in existing]
if missing: raise RuntimeError("جداول ناقصة: "+",".join(missing))

# تحقق أساسي من توازن القيود عند وجودها
bad=c.execute("""
SELECT journal_entry_id
FROM journal_entry_lines
GROUP BY journal_entry_id
HAVING ROUND(SUM(debit),2) <> ROUND(SUM(credit),2)
LIMIT 1
""").fetchone()

if bad:
    raise RuntimeError("يوجد قيد محاسبي غير متوازن: "+str(bad[0]))

if c.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
    raise RuntimeError("فشل integrity_check")

c.close()

sf=ROOT/".lulu_state"/"build_state.json"
state=json.loads(sf.read_text(encoding="utf-8"))
state["last_completed_stage"]=10
state["last_completed_at"]=datetime.now().isoformat()
state["accounting_base"]="Saudi_Riyal"
state["default_tax_rate"]=15
sf.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding="utf-8")

print("ACCOUNT TYPES: OK")
print("CHART OF ACCOUNTS: OK")
print("COST CENTERS: OK")
print("FISCAL YEARS: OK")
print("ACCOUNTING PERIODS: OK")
print("JOURNAL STRUCTURE: OK")
print("ACCOUNTING BALANCE CHECK: OK")
print("INTEGRITY: OK")
print("STATE: UPDATED")
print("STATUS: SUCCESS")
