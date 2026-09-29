from pathlib import Path
import sqlite3,json
from datetime import datetime

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/"database"/"nizam_alqirtasiyah.db"
c=sqlite3.connect(DB)
c.execute("PRAGMA foreign_keys=ON")

c.executescript("""
CREATE TABLE IF NOT EXISTS banks(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name VARCHAR(200) NOT NULL UNIQUE,
 code VARCHAR(50),
 is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS bank_accounts(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 bank_id INTEGER NOT NULL,
 branch_id INTEGER,
 account_name VARCHAR(200) NOT NULL,
 account_number VARCHAR(100),
 iban VARCHAR(100),
 currency_code VARCHAR(10) DEFAULT 'SAR',
 opening_balance NUMERIC NOT NULL DEFAULT 0,
 current_balance NUMERIC NOT NULL DEFAULT 0,
 is_active INTEGER NOT NULL DEFAULT 1,
 FOREIGN KEY(bank_id) REFERENCES banks(id),
 FOREIGN KEY(branch_id) REFERENCES branches(id)
);

CREATE TABLE IF NOT EXISTS bank_transactions(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 bank_account_id INTEGER NOT NULL,
 transaction_type VARCHAR(50) NOT NULL,
 amount NUMERIC NOT NULL,
 reference_type VARCHAR(100),
 reference_id INTEGER,
 description TEXT,
 transaction_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(bank_account_id) REFERENCES bank_accounts(id)
);

CREATE TABLE IF NOT EXISTS bank_reconciliations(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 bank_account_id INTEGER NOT NULL,
 statement_date TEXT NOT NULL,
 statement_balance NUMERIC NOT NULL,
 system_balance NUMERIC NOT NULL,
 difference NUMERIC NOT NULL,
 status VARCHAR(50) NOT NULL DEFAULT 'draft',
 notes TEXT,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(bank_account_id) REFERENCES bank_accounts(id)
);

CREATE INDEX IF NOT EXISTS idx_bank_transactions_account ON bank_transactions(bank_account_id);
CREATE INDEX IF NOT EXISTS idx_bank_transactions_date ON bank_transactions(transaction_date);
""")

c.execute("""
INSERT OR IGNORE INTO banks(name,code)
VALUES('البنك الرئيسي','MAIN-BANK')
""")

bank=c.execute("SELECT id FROM banks WHERE code='MAIN-BANK'").fetchone()[0]
branch=c.execute("SELECT id FROM branches WHERE code='MAIN'").fetchone()[0]

c.execute("""
INSERT OR IGNORE INTO bank_accounts
(bank_id,branch_id,account_name,account_number,iban)
VALUES(?,?,?,?,?)
""",(bank,branch,"الحساب البنكي الرئيسي","",""))

c.commit()

required=["banks","bank_accounts","bank_transactions","bank_reconciliations","cash_registers","cash_sessions","cash_transactions"]
existing={x[0] for x in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
missing=[x for x in required if x not in existing]
if missing: raise RuntimeError("جداول ناقصة: "+",".join(missing))
if c.execute("PRAGMA integrity_check").fetchone()[0]!="ok": raise RuntimeError("فشل integrity_check")

c.close()

sf=ROOT/".lulu_state"/"build_state.json"
state=json.loads(sf.read_text(encoding="utf-8"))
state["last_completed_stage"]=9
state["last_completed_at"]=datetime.now().isoformat()
sf.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding="utf-8")

print("CASH: OK")
print("BANKS: OK")
print("BANK ACCOUNTS: OK")
print("BANK TRANSACTIONS: OK")
print("RECONCILIATION: OK")
print("INTEGRITY: OK")
print("STATE: UPDATED")
print("STATUS: SUCCESS")
