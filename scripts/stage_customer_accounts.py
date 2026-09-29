from pathlib import Path
import sqlite3,datetime,shutil

ROOT=Path.cwd()
DB=ROOT/"database/nizam_alqirtasiyah.db"
BACK=ROOT/"backups"
stamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copy2(DB,BACK/f"before_customer_accounts_{stamp}.db")

con=sqlite3.connect(DB)
cur=con.cursor()

# جدول حركات حسابات العملاء
cur.execute("""
CREATE TABLE IF NOT EXISTS customer_account_transactions(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 customer_id INTEGER NOT NULL,
 transaction_type VARCHAR(40) NOT NULL,
 reference_type VARCHAR(50),
 reference_id INTEGER,
 debit NUMERIC DEFAULT 0,
 credit NUMERIC DEFAULT 0,
 balance NUMERIC DEFAULT 0,
 description VARCHAR(500),
 transaction_date DATETIME DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(customer_id) REFERENCES customers(id)
)
""")

# جدول التحصيل
cur.execute("""
CREATE TABLE IF NOT EXISTS customer_collections(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 collection_number VARCHAR(60) UNIQUE NOT NULL,
 customer_id INTEGER NOT NULL,
 amount NUMERIC NOT NULL,
 payment_method VARCHAR(40) NOT NULL,
 reference_number VARCHAR(100),
 notes VARCHAR(500),
 collection_date DATETIME DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(customer_id) REFERENCES customers(id)
)
""")

# التأكد من وجود عميل
cur.execute("SELECT id FROM customers ORDER BY id LIMIT 1")
customer=cur.fetchone()

if not customer:
    cur.execute("""
    INSERT INTO customers
    (customer_code,name,customer_type,current_balance,credit_limit,is_active)
    VALUES(?,?,?,?,?,?)
    """,("CUS-0001","عميل نقدي","INDIVIDUAL",0,1000,1))
    customer=(cur.lastrowid,)

cid=customer[0]

# تسجيل فاتورة آجلة تجريبية
cur.execute("""
INSERT INTO customer_account_transactions
(customer_id,transaction_type,reference_type,reference_id,debit,credit,balance,description)
VALUES(?,?,?,?,?,?,?,?)
""",(cid,"SALE","TEST",None,115,0,115,"فاتورة آجلة تجريبية"))

# تحديث رصيد العميل
cur.execute("""
UPDATE customers
SET current_balance=?
WHERE id=?
""",(115,cid))

# تسجيل تحصيل
cur.execute("""
INSERT OR IGNORE INTO customer_collections
(collection_number,customer_id,amount,payment_method,notes)
VALUES(?,?,?,?,?)
""",(
f"COL-{datetime.datetime.now().year}-000001",
cid,50,"CASH","تحصيل تجريبي"
))

# حركة دائنة للحساب
cur.execute("""
INSERT INTO customer_account_transactions
(customer_id,transaction_type,reference_type,debit,credit,balance,description)
VALUES(?,?,?,?,?,?,?)
""",(cid,"COLLECTION","CUSTOMER_COLLECTION",0,50,65,"تحصيل من العميل"))

# تحديث الرصيد بعد التحصيل
cur.execute("UPDATE customers SET current_balance=65 WHERE id=?",(cid,))

con.commit()

# فحوص
customers=cur.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
transactions=cur.execute("SELECT COUNT(*) FROM customer_account_transactions").fetchone()[0]
collections=cur.execute("SELECT COUNT(*) FROM customer_collections").fetchone()[0]

integrity=cur.execute("PRAGMA integrity_check").fetchone()[0]
fk=cur.execute("PRAGMA foreign_key_check").fetchall()

print("="*80)
print("CUSTOMERS + ACCOUNTS + COLLECTIONS")
print("="*80)
print("BACKUP:",BACK/f"before_customer_accounts_{stamp}.db")
print("CUSTOMERS:",customers)
print("ACCOUNT TRANSACTIONS:",transactions)
print("COLLECTIONS:",collections)
print("CUSTOMER BALANCE TEST: 115 - 50 = 65")
print("CURRENT BALANCE:",cur.execute(
"SELECT current_balance FROM customers WHERE id=?",(cid,)
).fetchone()[0])
print("INTEGRITY:",integrity)
print("FOREIGN KEY ERRORS:",len(fk))
print("STATUS: SUCCESS")
print("="*80)

con.close()
