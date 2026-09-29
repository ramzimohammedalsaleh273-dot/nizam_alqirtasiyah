import sqlite3,datetime,shutil
from pathlib import Path

R=Path.cwd(); DB=R/"database/nizam_alqirtasiyah.db"; B=R/"backups"
ts=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copy2(DB,B/f"before_print_fix_{ts}.db")

c=sqlite3.connect(DB); q=c.cursor()

q.execute("""CREATE TABLE IF NOT EXISTS erp_print_templates(
id INTEGER PRIMARY KEY AUTOINCREMENT,
code VARCHAR(60) UNIQUE NOT NULL,
name VARCHAR(200) NOT NULL,
document_type VARCHAR(50),
is_default INTEGER DEFAULT 0,
is_active INTEGER DEFAULT 1)""")

q.execute("""CREATE TABLE IF NOT EXISTS erp_report_exports(
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

q.executemany("""INSERT OR IGNORE INTO erp_print_templates
(code,name,document_type,is_default)
VALUES(?,?,?,?)""",templates)

out=R/"reports"; out.mkdir(exist_ok=True)

sales=q.execute("""
SELECT invoice_number,subtotal,tax_amount,total_amount,paid_amount,due_amount,created_at
FROM sales ORDER BY id
""").fetchall()

csv=out/"sales_report.csv"
with open(csv,"w",encoding="utf-8-sig") as f:
    f.write("رقم الفاتورة,قبل الضريبة,الضريبة,الإجمالي,المدفوع,المتبقي,التاريخ\n")
    for row in sales:
        f.write(",".join("" if x is None else str(x) for x in row)+"\n")

q.execute("""INSERT INTO erp_report_exports
(report_code,file_format,file_path)
VALUES(?,?,?)""",("SALES_REPORT","CSV",str(csv)))

c.commit()

integrity=q.execute("PRAGMA integrity_check").fetchone()[0]
fk=q.execute("PRAGMA foreign_key_check").fetchall()

print("="*75)
print("PRINT + REPORTS REPAIR")
print("="*75)
print("BACKUP:",B/f"before_print_fix_{ts}.db")
print("PRINT TEMPLATES:",q.execute("SELECT COUNT(*) FROM erp_print_templates").fetchone()[0])
print("SALES REPORT:",csv)
print("INTEGRITY:",integrity)
print("FOREIGN KEY ERRORS:",len(fk))
print("STATUS: SUCCESS" if integrity=="ok" and not fk else "STATUS: FAILED")
print("="*75)
c.close()
