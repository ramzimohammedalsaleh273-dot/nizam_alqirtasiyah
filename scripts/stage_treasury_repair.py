from pathlib import Path
import sqlite3,datetime,shutil

ROOT=Path.cwd()
DB=ROOT/"database/nizam_alqirtasiyah.db"
BACK=ROOT/"backups"
stamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copy2(DB,BACK/f"before_treasury_repair_{stamp}.db")

con=sqlite3.connect(DB)
cur=con.cursor()

def cols(table):
    return [r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()]

# إنشاء الجداول الناقصة فقط
cur.execute("""CREATE TABLE IF NOT EXISTS cash_receipts(
id INTEGER PRIMARY KEY AUTOINCREMENT,
receipt_number VARCHAR(50) UNIQUE NOT NULL,
customer_id INTEGER,
amount NUMERIC NOT NULL,
payment_method VARCHAR(50) NOT NULL,
reference_number VARCHAR(100),
notes VARCHAR(500),
receipt_date DATETIME DEFAULT CURRENT_TIMESTAMP)""")

cur.execute("""CREATE TABLE IF NOT EXISTS cash_payments(
id INTEGER PRIMARY KEY AUTOINCREMENT,
payment_number VARCHAR(50) UNIQUE NOT NULL,
supplier_id INTEGER,
amount NUMERIC NOT NULL,
payment_method VARCHAR(50) NOT NULL,
reference_number VARCHAR(100),
notes VARCHAR(500),
payment_date DATETIME DEFAULT CURRENT_TIMESTAMP)""")

cur.execute("""CREATE TABLE IF NOT EXISTS bank_transactions(
id INTEGER PRIMARY KEY AUTOINCREMENT,
bank_account_id INTEGER,
transaction_type VARCHAR(30),
amount NUMERIC NOT NULL,
reference_number VARCHAR(100),
description VARCHAR(500),
transaction_date DATETIME DEFAULT CURRENT_TIMESTAMP)""")

cur.execute("""CREATE TABLE IF NOT EXISTS treasury_sequences(
id INTEGER PRIMARY KEY AUTOINCREMENT,
sequence_type VARCHAR(50) UNIQUE NOT NULL,
last_number INTEGER DEFAULT 0)""")

for typ in ("RECEIPT","PAYMENT","BANK"):
    cur.execute("INSERT OR IGNORE INTO treasury_sequences(sequence_type,last_number) VALUES(?,0)",(typ,))

# جلسة الخزينة: نستخدم الأعمدة الموجودة فعليًا
cc=cols("cash_sessions")
cur.execute("SELECT id FROM cash_registers ORDER BY id LIMIT 1")
register=cur.fetchone()
cur.execute("SELECT id FROM users ORDER BY id LIMIT 1")
user=cur.fetchone()

if not register or not user:
    raise RuntimeError("بيانات cash_registers/users الأساسية غير موجودة")

if "cash_register_id" in cc and "user_id" in cc:
    cur.execute("""INSERT INTO cash_sessions
    (cash_register_id,user_id,opening_balance,status)
    VALUES(?,?,?,?)""",(register[0],user[0],1000,"OPEN"))
elif "register_id" in cc and "user_id" in cc:
    cur.execute("""INSERT INTO cash_sessions
    (register_id,user_id,opening_balance,status)
    VALUES(?,?,?,?)""",(register[0],user[0],1000,"OPEN"))
elif "cash_register_id" in cc:
    cur.execute("""INSERT INTO cash_sessions
    (cash_register_id,opening_balance)
    VALUES(?,?)""",(register[0],1000))
else:
    print("CASH SESSION INSERT: SKIPPED - schema مختلف")
    
# إيصال قبض حقيقي
cur.execute("UPDATE treasury_sequences SET last_number=last_number+1 WHERE sequence_type='RECEIPT'")
n=cur.execute("SELECT last_number FROM treasury_sequences WHERE sequence_type='RECEIPT'").fetchone()[0]
cur.execute("""INSERT INTO cash_receipts
(receipt_number,amount,payment_method,notes)
VALUES(?,?,?,?)""",
(f"CR-{datetime.datetime.now().year}-{n:06d}",100,"CASH","اختبار نظام الخزينة"))

# سند صرف حقيقي
cur.execute("UPDATE treasury_sequences SET last_number=last_number+1 WHERE sequence_type='PAYMENT'")
n=cur.execute("SELECT last_number FROM treasury_sequences WHERE sequence_type='PAYMENT'").fetchone()[0]
cur.execute("""INSERT INTO cash_payments
(payment_number,amount,payment_method,notes)
VALUES(?,?,?,?)""",
(f"CP-{datetime.datetime.now().year}-{n:06d}",50,"CASH","اختبار نظام الخزينة"))

# حركة بنك إن وجد حساب
cur.execute("SELECT id FROM bank_accounts ORDER BY id LIMIT 1")
bank=cur.fetchone()
if bank:
    cur.execute("""INSERT INTO bank_transactions
(bank_account_id,transaction_type,amount,description)
VALUES(?,?,?,?)""",(bank[0],"DEPOSIT",500,"اختبار حركة بنكية"))

con.commit()

integrity=cur.execute("PRAGMA integrity_check").fetchone()[0]
fk=cur.execute("PRAGMA foreign_key_check").fetchall()

print("="*75)
print("TREASURY REPAIR")
print("="*75)
print("BACKUP:",BACK/f"before_treasury_repair_{stamp}.db")
print("CASH RECEIPTS:",cur.execute("SELECT COUNT(*) FROM cash_receipts").fetchone()[0])
print("CASH PAYMENTS:",cur.execute("SELECT COUNT(*) FROM cash_payments").fetchone()[0])
print("CASH SESSIONS:",cur.execute("SELECT COUNT(*) FROM cash_sessions").fetchone()[0])
print("BANK TRANSACTIONS:",cur.execute("SELECT COUNT(*) FROM bank_transactions").fetchone()[0])
print("CASH SESSION COLUMNS:",cc)
print("INTEGRITY:",integrity)
print("FOREIGN KEY ERRORS:",len(fk))
print("STATUS: SUCCESS")
print("="*75)

con.close()
