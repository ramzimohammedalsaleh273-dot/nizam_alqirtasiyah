import sqlite3,datetime,shutil
from pathlib import Path

R=Path.cwd(); DB=R/"database/nizam_alqirtasiyah.db"; B=R/"backups"
ts=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copy2(DB,B/f"before_accounting_fix_{ts}.db")

c=sqlite3.connect(DB); q=c.cursor()

def cols(t):
    return [x[1] for x in q.execute(f"PRAGMA table_info({t})").fetchall()]

# جدول التقارير: إنشاء جدول مستقل متوافق بدل تغيير الموجود
q.execute("""
CREATE TABLE IF NOT EXISTS erp_report_catalog(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 report_code VARCHAR(60) UNIQUE NOT NULL,
 report_name VARCHAR(200) NOT NULL,
 report_type VARCHAR(50),
 is_active INTEGER DEFAULT 1
)""")

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
("SUPPLIER_AGING","أعمار ديون الموردين","SUPPLIER")
]
q.executemany(
"INSERT OR IGNORE INTO erp_report_catalog(report_code,report_name,report_type) VALUES(?,?,?)",
reports
)

# حساب الأرصدة من القيود الحالية
q.execute("SELECT COALESCE(SUM(debit),0),COALESCE(SUM(credit),0) FROM journal_entry_lines")
debit,credit=q.fetchone()

integrity=q.execute("PRAGMA integrity_check").fetchone()[0]
fk=q.execute("PRAGMA foreign_key_check").fetchall()

c.commit()

print("="*75)
print("ACCOUNTING REPAIR")
print("="*75)
print("BACKUP:",B/f"before_accounting_fix_{ts}.db")
print("TOTAL DEBIT :",debit)
print("TOTAL CREDIT:",credit)
print("TRIAL BALANCE:","BALANCED" if abs(debit-credit)<0.001 else "UNBALANCED")
print("REPORT CATALOG:",q.execute("SELECT COUNT(*) FROM erp_report_catalog").fetchone()[0])
print("INTEGRITY:",integrity)
print("FOREIGN KEY ERRORS:",len(fk))
print("STATUS: SUCCESS" if integrity=="ok" and not fk and abs(debit-credit)<0.001 else "STATUS: FAILED")
print("="*75)

c.close()
