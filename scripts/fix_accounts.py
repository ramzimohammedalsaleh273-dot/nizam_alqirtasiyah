from pathlib import Path
import sqlite3,json
from datetime import datetime

R=Path(__file__).resolve().parents[1]
D=R/"database"/"nizam_alqirtasiyah.db"

c=sqlite3.connect(D)

c.execute("""
CREATE TABLE IF NOT EXISTS accounts(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_code TEXT UNIQUE NOT NULL,
    account_name TEXT NOT NULL,
    account_type TEXT NOT NULL,
    parent_id INTEGER,
    is_active INTEGER DEFAULT 1,
    allow_posting INTEGER DEFAULT 1,
    opening_balance REAL DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

c.execute("""
CREATE INDEX IF NOT EXISTS idx_accounts_parent
ON accounts(parent_id)
""")

c.execute("""
CREATE INDEX IF NOT EXISTS idx_accounts_type
ON accounts(account_type)
""")

accounts=[
    ("1100","الخزينة","asset"),
    ("1200","البنوك","asset"),
    ("1300","العملاء","asset"),
    ("1400","المخزون","asset"),
    ("2100","الموردون","liability"),
    ("4100","مبيعات القرطاسية","revenue"),
    ("4200","خدمات الطباعة","revenue"),
    ("5100","تكلفة البضاعة المباعة","expense")
]

for code,name,atype in accounts:
    c.execute("""
        INSERT OR IGNORE INTO accounts
        (account_code,account_name,account_type)
        VALUES(?,?,?)
    """,(code,name,atype))

if c.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
    c.close()
    raise RuntimeError("فشل integrity_check")

c.commit()
c.close()

sf=R/".lulu_state"/"build_state.json"
st=json.loads(sf.read_text(encoding="utf-8"))

if st.get("last_completed_stage",0)<29:
    raise RuntimeError("المرحلة 29 غير مكتملة")

print("ACCOUNTS TABLE: OK")
print("CHART OF ACCOUNTS: OK")
print("ACCOUNT INDEXES: OK")
print("ACCOUNTING DATA: OK")
print("INTEGRITY: OK")
print("STATUS: SUCCESS")
