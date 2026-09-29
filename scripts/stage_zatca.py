import sqlite3,datetime,shutil
from pathlib import Path

R=Path.cwd(); DB=R/"database/nizam_alqirtasiyah.db"; B=R/"backups"
ts=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copy2(DB,B/f"before_zatca_stage_{ts}.db")

c=sqlite3.connect(DB); q=c.cursor()

q.execute("""
CREATE TABLE IF NOT EXISTS e_invoices(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 invoice_number VARCHAR(100) UNIQUE NOT NULL,
 invoice_type VARCHAR(30) DEFAULT 'STANDARD',
 sale_id INTEGER,
 customer_id INTEGER,
 uuid VARCHAR(100),
 issue_date DATETIME DEFAULT CURRENT_TIMESTAMP,
 subtotal NUMERIC DEFAULT 0,
 tax_amount NUMERIC DEFAULT 0,
 total_amount NUMERIC DEFAULT 0,
 status VARCHAR(30) DEFAULT 'DRAFT',
 qr_data TEXT,
 xml_data TEXT
)""")

q.execute("""
CREATE TABLE IF NOT EXISTS e_invoice_lines(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 e_invoice_id INTEGER NOT NULL,
 product_id INTEGER,
 description VARCHAR(500),
 quantity NUMERIC DEFAULT 0,
 unit_price NUMERIC DEFAULT 0,
 tax_rate NUMERIC DEFAULT 15,
 tax_amount NUMERIC DEFAULT 0,
 line_total NUMERIC DEFAULT 0,
 FOREIGN KEY(e_invoice_id) REFERENCES e_invoices(id)
)""")

q.execute("""
CREATE TABLE IF NOT EXISTS tax_config(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 tax_number VARCHAR(100),
 vat_rate NUMERIC DEFAULT 15,
 currency VARCHAR(10) DEFAULT 'SAR',
 country_code VARCHAR(5) DEFAULT 'SA',
 invoice_prefix VARCHAR(20) DEFAULT 'INV',
 is_active INTEGER DEFAULT 1
)""")

q.execute("""
CREATE TABLE IF NOT EXISTS zatca_settings(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 environment VARCHAR(30) DEFAULT 'SANDBOX',
 compliance_status VARCHAR(30) DEFAULT 'NOT_CONFIGURED',
 csr_status VARCHAR(30) DEFAULT 'NOT_CONFIGURED',
 reporting_status VARCHAR(30) DEFAULT 'NOT_CONFIGURED',
 clearance_status VARCHAR(30) DEFAULT 'NOT_CONFIGURED'
)""")

q.execute("""
INSERT INTO tax_config(tax_number,vat_rate,currency,country_code)
SELECT '',15,'SAR','SA'
WHERE NOT EXISTS (SELECT 1 FROM tax_config)
""")

q.execute("""
INSERT INTO zatca_settings(environment)
SELECT 'SANDBOX'
WHERE NOT EXISTS (SELECT 1 FROM zatca_settings)
""")

# تحويل الفاتورة الموجودة إلى سجل إلكتروني
sale=q.execute("""
SELECT id,invoice_number,customer_id,subtotal,tax_amount,total_amount
FROM sales ORDER BY id LIMIT 1
""").fetchone()

if sale:
    q.execute("""
    INSERT OR IGNORE INTO e_invoices
    (invoice_number,invoice_type,sale_id,customer_id,subtotal,tax_amount,total_amount,status)
    VALUES(?,?,?,?,?,?,?,'READY')
    """,(sale[1], "STANDARD", sale[0], sale[2],
         sale[3],sale[4],sale[5]))

# إضافة سطور الفاتورة
einv=q.execute("SELECT id FROM e_invoices ORDER BY id LIMIT 1").fetchone()
if einv:
    items=q.execute("""
    SELECT product_id,quantity,unit_price,tax_amount,line_total
    FROM sale_items WHERE sale_id=?
    """,(sale[0],)).fetchall() if sale else []

    for p,qty,price,tax,total in items:
        q.execute("""
        INSERT INTO e_invoice_lines
        (e_invoice_id,product_id,quantity,unit_price,tax_amount,line_total)
        VALUES(?,?,?,?,?,?)
        """,(einv[0],p,qty,price,tax,total))

c.commit()

integrity=q.execute("PRAGMA integrity_check").fetchone()[0]
fk=q.execute("PRAGMA foreign_key_check").fetchall()

print("="*80)
print("ZATCA + E-INVOICING STAGE")
print("="*80)
print("BACKUP:",B/f"before_zatca_stage_{ts}.db")
print("TAX CONFIG:",q.execute("SELECT COUNT(*) FROM tax_config").fetchone()[0])
print("ZATCA SETTINGS:",q.execute("SELECT COUNT(*) FROM zatca_settings").fetchone()[0])
print("E-INVOICES:",q.execute("SELECT COUNT(*) FROM e_invoices").fetchone()[0])
print("E-INVOICE LINES:",q.execute("SELECT COUNT(*) FROM e_invoice_lines").fetchone()[0])
print("VAT RATE: 15%")
print("CURRENCY: SAR")
print("ENVIRONMENT: SANDBOX")
print("INTEGRITY:",integrity)
print("FOREIGN KEY ERRORS:",len(fk))
print("STATUS: SUCCESS" if integrity=="ok" and not fk else "STATUS: FAILED")
print("="*80)
c.close()
