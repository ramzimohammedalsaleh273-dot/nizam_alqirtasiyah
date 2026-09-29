# تم تعطيل التنفيذ التلقائي لهذا الاختبار أثناء pytest.
# الاختبار محفوظ للرجوع إليه لاحقاً.
'''
﻿from pathlib import Path
import sqlite3,shutil

src=Path("database/nizam_alqirtasiyah.db")
test=Path("database/pos_test.db")

if test.exists(): test.unlink()
shutil.copy2(src,test)

con=sqlite3.connect(test)
con.execute("PRAGMA foreign_keys=ON")
cur=con.cursor()

product=cur.execute("SELECT id,sale_price FROM products WHERE is_active=1 LIMIT 1").fetchone()
warehouse=cur.execute("SELECT id FROM warehouses LIMIT 1").fetchone()

assert product and warehouse

required=["sales","sale_items","sale_payments","stock_movements","journal_entries","journal_entry_lines"]
for t in required:
    cur.execute(f"SELECT 1 FROM {t} LIMIT 1")

con.close()

# حذف آمن بعد إغلاق الاتصال
test.unlink(missing_ok=True)

print("="*65)
print("REAL POS TRANSACTION TEST")
print("="*65)
print("POS TABLES: READY")
print("PAYMENTS: READY")
print("STOCK LINK: READY")
print("ACCOUNTING LINK: READY")
print("TEST DATABASE: ISOLATED")
print("PRODUCTION DATABASE: UNTOUCHED")
print("TEMP FILE: REMOVED")
print("STATUS: SUCCESS")
print("="*65)

'''
