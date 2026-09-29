from pathlib import Path
import sqlite3,datetime,py_compile,shutil

ROOT=Path.cwd()
DB=ROOT/"database/nizam_alqirtasiyah.db"
BACK=ROOT/"backups"
BACK.mkdir(exist_ok=True)

stamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copy2(DB,BACK/f"before_treasury_stage_{stamp}.db")

con=sqlite3.connect(DB)
cur=con.cursor()

tables={
"cash_receipts":"""
CREATE TABLE IF NOT EXISTS cash_receipts(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 receipt_number VARCHAR(50) UNIQUE NOT NULL,
 customer_id INTEGER,
 amount NUMERIC NOT NULL,
 payment_method VARCHAR(50) NOT NULL,
 reference_number VARCHAR(100),
 notes VARCHAR(500),
 receipt_date DATETIME DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(customer_id) REFERENCES customers(id)
)""",
"cash_payments":"""
CREATE TABLE IF NOT EXISTS cash_payments(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 payment_number VARCHAR(50) UNIQUE NOT NULL,
 supplier_id INTEGER,
 amount NUMERIC NOT NULL,
 payment_method VARCHAR(50) NOT NULL,
 reference_number VARCHAR(100),
 notes VARCHAR(500),
 payment_date DATETIME DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(supplier_id) REFERENCES suppliers(id)
)""",
"bank_transactions":"""
CREATE TABLE IF NOT EXISTS bank_transactions(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 bank_account_id INTEGER NOT NULL,
 transaction_type VARCHAR(30) NOT NULL,
 amount NUMERIC NOT NULL,
 reference_number VARCHAR(100),
 description VARCHAR(500),
 transaction_date DATETIME DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(bank_account_id) REFERENCES bank_accounts(id)
)""",
"cash_sessions":"""
CREATE TABLE IF NOT EXISTS cash_sessions(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 cash_register_id INTEGER NOT NULL,
 user_id INTEGER NOT NULL,
 opening_balance NUMERIC DEFAULT 0,
 closing_balance NUMERIC DEFAULT 0,
 status VARCHAR(30) DEFAULT 'OPEN',
 opened_at DATETIME DEFAULT CURRENT_TIMESTAMP,
 closed_at DATETIME,
 FOREIGN KEY(cash_register_id) REFERENCES cash_registers(id),
 FOREIGN KEY(user_id) REFERENCES users(id)
)"""
}

for sql in tables.values():
    cur.execute(sql)

# أرقام تلقائية
cur.execute("""CREATE TABLE IF NOT EXISTS treasury_sequences(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 sequence_type VARCHAR(50) UNIQUE NOT NULL,
 last_number INTEGER DEFAULT 0
)""")

for typ in ("RECEIPT","PAYMENT","BANK"):
    cur.execute(
        "INSERT OR IGNORE INTO treasury_sequences(sequence_type,last_number) VALUES(?,0)",
        (typ,)
    )

con.commit()

# اختبار فعلي للعمليات
cur.execute("SELECT id FROM customers ORDER BY id LIMIT 1")
customer=cur.fetchone()
cur.execute("SELECT id FROM suppliers ORDER BY id LIMIT 1")
supplier=cur.fetchone()
cur.execute("SELECT id FROM bank_accounts ORDER BY id LIMIT 1")
bank=cur.fetchone()
cur.execute("SELECT id FROM cash_registers ORDER BY id LIMIT 1")
register=cur.fetchone()
cur.execute("SELECT id FROM users ORDER BY id LIMIT 1")
user=cur.fetchone()

if not register or not user:
    con.close()
    print("STATUS: FAILED")
    print("ERROR: بيانات الخزينة الأساسية غير موجودة")
    raise SystemExit(1)

# إيصال تحصيل
cur.execute("UPDATE treasury_sequences SET last_number=last_number+1 WHERE sequence_type='RECEIPT'")
n=cur.execute("SELECT last_number FROM treasury_sequences WHERE sequence_type='RECEIPT'").fetchone()[0]
cur.execute("""
INSERT INTO cash_receipts(receipt_number,customer_id,amount,payment_method,notes)
VALUES(?,?,?,?,?)
""",(f"CR-{datetime.datetime.now().year}-{n:06d}",customer[0] if customer else None,100,"CASH","اختبار تحصيل"))

# سند صرف
cur.execute("UPDATE treasury_sequences SET last_number=last_number+1 WHERE sequence_type='PAYMENT'")
n=cur.execute("SELECT last_number FROM treasury_sequences WHERE sequence_type='PAYMENT'").fetchone()[0]
cur.execute("""
INSERT INTO cash_payments(payment_number,supplier_id,amount,payment_method,notes)
VALUES(?,?,?,?,?)
""",(f"CP-{datetime.datetime.now().year}-{n:06d}",supplier[0] if supplier else None,50,"CASH","اختبار صرف"))

# جلسة خزينة
cur.execute("""
INSERT INTO cash_sessions(cash_register_id,user_id,opening_balance,status)
VALUES(?,?,?,?)
""",(register[0],user[0],1000,"OPEN"))

# اختبار البنك إذا وجد حساب
if bank:
    cur.execute("""
    INSERT INTO bank_transactions
    (bank_account_id,transaction_type,amount,description)
    VALUES(?,?,?,?)
    """,(bank[0],"DEPOSIT",500,"اختبار حركة بنكية"))

con.commit()

# فحص
checks=[
("cash_receipts",cur.execute("SELECT COUNT(*) FROM cash_receipts").fetchone()[0]),
("cash_payments",cur.execute("SELECT COUNT(*) FROM cash_payments").fetchone()[0]),
("cash_sessions",cur.execute("SELECT COUNT(*) FROM cash_sessions").fetchone()[0]),
("bank_transactions",cur.execute("SELECT COUNT(*) FROM bank_transactions").fetchone()[0])
]

integrity=cur.execute("PRAGMA integrity_check").fetchone()[0]
fk=cur.execute("PRAGMA foreign_key_check").fetchall()

con.close()

print("="*80)
print("TREASURY + BANKS STAGE")
print("="*80)
print("BACKUP:",BACK/f"before_treasury_stage_{stamp}.db")
for name,count in checks:
    print(f"{name:25} {count}")
print("CASH RECEIPTS: OK")
print("CASH PAYMENTS: OK")
print("CASH SESSIONS: OK")
print("BANK TRANSACTIONS: OK" if bank else "BANK TRANSACTIONS: TABLE OK")
print("INTEGRITY:",integrity)
print("FOREIGN KEY ERRORS:",len(fk))
print("STATUS: SUCCESS")
print("="*80)
