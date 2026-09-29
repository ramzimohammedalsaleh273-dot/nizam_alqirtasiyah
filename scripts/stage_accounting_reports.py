import sqlite3,datetime,shutil
from pathlib import Path

R=Path.cwd(); DB=R/"database/nizam_alqirtasiyah.db"; B=R/"backups"
ts=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copy2(DB,B/f"before_accounting_reports_{ts}.db")
c=sqlite3.connect(DB); q=c.cursor()

q.execute("""CREATE TABLE IF NOT EXISTS fiscal_periods(
id INTEGER PRIMARY KEY AUTOINCREMENT,
period_name VARCHAR(50) UNIQUE, start_date DATE, end_date DATE,
status VARCHAR(20) DEFAULT 'OPEN')""")

q.execute("""CREATE TABLE IF NOT EXISTS cost_centers(
id INTEGER PRIMARY KEY AUTOINCREMENT,
code VARCHAR(50) UNIQUE,name VARCHAR(200),is_active INTEGER DEFAULT 1)""")

q.execute("""CREATE TABLE IF NOT EXISTS account_balances(
id INTEGER PRIMARY KEY AUTOINCREMENT,
account_id INTEGER NOT NULL,fiscal_period_id INTEGER,
debit NUMERIC DEFAULT 0,credit NUMERIC DEFAULT 0,
balance NUMERIC DEFAULT 0,
FOREIGN KEY(account_id) REFERENCES accounts(id),
FOREIGN KEY(fiscal_period_id) REFERENCES fiscal_periods(id))""")

year=datetime.datetime.now().year
q.execute("INSERT OR IGNORE INTO fiscal_periods(period_name,start_date,end_date,status) VALUES(?,?,?,'OPEN')",
          (f"{year}",f"{year}-01-01",f"{year}-12-31"))

# إعادة بناء أرصدة الحسابات من القيود الموجودة
period=q.execute("SELECT id FROM fiscal_periods WHERE period_name=?",(str(year),)).fetchone()[0]
q.execute("DELETE FROM account_balances")
accounts=q.execute("SELECT id FROM accounts").fetchall()

for (aid,) in accounts:
    d=q.execute("SELECT COALESCE(SUM(debit),0) FROM journal_entry_lines WHERE account_id=?",(aid,)).fetchone()[0]
    cr=q.execute("SELECT COALESCE(SUM(credit),0) FROM journal_entry_lines WHERE account_id=?",(aid,)).fetchone()[0]
    q.execute("""INSERT INTO account_balances
    (account_id,fiscal_period_id,debit,credit,balance)
    VALUES(?,?,?,?,?)""",(aid,period,d,cr,d-cr))

c.commit()

debit=q.execute("SELECT COALESCE(SUM(debit),0) FROM journal_entry_lines").fetchone()[0]
credit=q.execute("SELECT COALESCE(SUM(credit),0) FROM journal_entry_lines").fetchone()[0]
accounts_count=q.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
journals=q.execute("SELECT COUNT(*) FROM journal_entries").fetchone()[0]
lines=q.execute("SELECT COUNT(*) FROM journal_entry_lines").fetchone()[0]

# تقارير أساسية محفوظة كاستعلامات قابلة لإعادة الاستخدام
q.execute("""CREATE TABLE IF NOT EXISTS report_definitions(
id INTEGER PRIMARY KEY AUTOINCREMENT,
report_code VARCHAR(60) UNIQUE,report_name VARCHAR(200),
report_type VARCHAR(50),is_active INTEGER DEFAULT 1)""")

reports=[
("GENERAL_LEDGER","دفتر الأستاذ العام","ACCOUNTING"),
("TRIAL_BALANCE","ميزان المراجعة","ACCOUNTING"),
("INCOME_STATEMENT","قائمة الدخل","FINANCIAL"),
("BALANCE_SHEET","الميزانية العمومية","FINANCIAL"),
("CASH_FLOW","قائمة التدفقات النقدية","FINANCIAL"),
("SALES_REPORT","تقرير المبيعات","SALES"),
("PURCHASE_REPORT","تقرير المشتريات","PURCHASE"),
("INVENTORY_REPORT","تقرير المخزون","INVENTORY"),
("CUSTOMER_AGING","أعمار ديون العملاء","CUSTOMER"),
("SUPPLIER_AGING","أعمار ديون الموردين","SUPPLIER")]
q.executemany("INSERT OR IGNORE INTO report_definitions(report_code,report_name,report_type) VALUES(?,?,?)",reports)
c.commit()

integrity=q.execute("PRAGMA integrity_check").fetchone()[0]
fk=q.execute("PRAGMA foreign_key_check").fetchall()

print("="*80)
print("ACCOUNTING + FINANCIAL REPORTS")
print("="*80)
print("BACKUP:",B/f"before_accounting_reports_{ts}.db")
print("ACCOUNTS:",accounts_count)
print("JOURNAL ENTRIES:",journals)
print("JOURNAL LINES:",lines)
print("TOTAL DEBIT :",debit)
print("TOTAL CREDIT:",credit)
print("TRIAL BALANCE:", "BALANCED" if abs(debit-credit)<0.001 else "UNBALANCED")
print("REPORTS:",q.execute("SELECT COUNT(*) FROM report_definitions").fetchone()[0])
print("INTEGRITY:",integrity)
print("FOREIGN KEY ERRORS:",len(fk))
print("STATUS: SUCCESS" if integrity=="ok" and not fk and abs(debit-credit)<0.001 else "STATUS: FAILED")
print("="*80)
c.close()
