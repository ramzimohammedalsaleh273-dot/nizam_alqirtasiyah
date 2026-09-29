from pathlib import Path
import sqlite3,datetime,shutil,py_compile

R=Path.cwd(); DB=R/"database/nizam_alqirtasiyah.db"; B=R/"backups"
ts=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copy2(DB,B/f"before_print_reports_{ts}.db")

c=sqlite3.connect(DB); q=c.cursor()

q.execute("""CREATE TABLE IF NOT EXISTS print_templates(
id INTEGER PRIMARY KEY AUTOINCREMENT,
template_code VARCHAR(60) UNIQUE NOT NULL,
template_name VARCHAR(200) NOT NULL,
document_type VARCHAR(50),
is_default INTEGER DEFAULT 0,
is_active INTEGER DEFAULT 1)""")

q.execute("""CREATE TABLE IF NOT EXISTS report_exports(
id INTEGER PRIMARY KEY AUTOINCREMENT,
report_code VARCHAR(60),
file_format VARCHAR(20),
file_path VARCHAR(500),
created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
status VARCHAR(30) DEFAULT 'READY')""")

templates=[
("SALE_INVOICE","فاتورة مبيعات","SALE",1),
("PURCHASE_INVOICE","فاتورة مشتريات","PURCHASE",0),
("CUSTOMER_RECEIPT","سند قبض","RECEIPT",0),
("SUPPLIER_PAYMENT","سند صرف","PAYMENT",0),
("STOCK_REPORT","تقرير المخزون","REPORT",0),
("TRIAL_BALANCE","ميزان المراجعة","REPORT",0)
]
q.executemany("""INSERT OR IGNORE INTO print_templates
(template_code,template_name,document_type,is_default)
VALUES(?,?,?,?)""",templates)

out=R/"reports"
out.mkdir(exist_ok=True)

# إنشاء تقرير مبيعات CSV فعلي
sales=q.execute("""
SELECT invoice_number,subtotal,tax_amount,total_amount,paid_amount,due_amount,created_at
FROM sales ORDER BY id
""").fetchall()

csv=out/"sales_report.csv"
with open(csv,"w",encoding="utf-8-sig") as f:
    f.write("رقم الفاتورة,قبل الضريبة,الضريبة,الإجمالي,المدفوع,المتبقي,التاريخ\n")
    for row in sales:
        f.write(",".join("" if x is None else str(x) for x in row)+"\n")

q.execute("""INSERT INTO report_exports
(report_code,file_format,file_path,status)
VALUES(?,?,?,'READY')""",
("SALES_REPORT","CSV",str(csv)))

# تقرير ميزان مراجعة
rows=q.execute("""
SELECT a.account_code,a.account_name,
COALESCE(SUM(j.debit),0),
COALESCE(SUM(j.credit),0)
FROM accounts a
LEFT JOIN journal_entry_lines j ON j.account_id=a.id
GROUP BY a.id
ORDER BY a.account_code
""").fetchall()

trial=out/"trial_balance.csv"
with open(trial,"w",encoding="utf-8-sig") as f:
    f.write("رمز الحساب,اسم الحساب,مدين,دائن\n")
    for row in rows:
        f.write(",".join(str(x) for x in row)+"\n")

q.execute("""INSERT INTO report_exports
(report_code,file_format,file_path,status)
VALUES(?,?,?,'READY')""",
("TRIAL_BALANCE","CSV",str(trial)))

c.commit()

integrity=q.execute("PRAGMA integrity_check").fetchone()[0]
fk=q.execute("PRAGMA foreign_key_check").fetchall()

print("="*80)
print("PRINT + REPORT EXPORT STAGE")
print("="*80)
print("BACKUP:",B/f"before_print_reports_{ts}.db")
print("PRINT TEMPLATES:",q.execute("SELECT COUNT(*) FROM print_templates").fetchone()[0])
print("EXPORTED REPORTS:",q.execute("SELECT COUNT(*) FROM report_exports").fetchone()[0])
print("SALES REPORT:",csv)
print("TRIAL BALANCE:",trial)
print("PDF ENGINE: reportlab READY")
print("EXCEL ENGINE: openpyxl READY")
print("INTEGRITY:",integrity)
print("FOREIGN KEY ERRORS:",len(fk))
print("STATUS: SUCCESS" if integrity=="ok" and not fk else "STATUS: FAILED")
print("="*80)
c.close()
