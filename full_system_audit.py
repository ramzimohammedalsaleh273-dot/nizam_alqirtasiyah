import sqlite3

DB=r"database\nizam_alqirtasiyah.db"
c=sqlite3.connect(DB)
x=c.cursor()

print("="*75)
print("          التدقيق الشامل لنظام القرطاسية")
print("="*75)

errors=[]
warnings=[]

def check(name,condition,detail):
    if condition:
        print(f"[OK] {name}: {detail}")
    else:
        print(f"[تحذير] {name}: {detail}")
        warnings.append((name,detail))

# ------------------------------------------------------------
# 1) سلامة SQLite
# ------------------------------------------------------------
integrity=x.execute("PRAGMA integrity_check").fetchone()[0]
fk=x.execute("PRAGMA foreign_key_check").fetchall()

check("سلامة SQLite",integrity=="ok",integrity)
check("العلاقات الخارجية",len(fk)==0,f"{len(fk)} أخطاء")

# ------------------------------------------------------------
# 2) الجداول
# ------------------------------------------------------------
tables=x.execute("""
SELECT name FROM sqlite_master
WHERE type='table' AND name NOT LIKE 'sqlite_%'
ORDER BY name
""").fetchall()

empty=[]
filled=[]

for (t,) in tables:
    try:
        n=x.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        if n==0:
            empty.append(t)
        else:
            filled.append((t,n))
    except:
        pass

print("\n=== الجداول ===")
print("إجمالي الجداول:",len(tables))
print("جداول بها بيانات:",len(filled))
print("جداول فارغة:",len(empty))

# ------------------------------------------------------------
# 3) القيود المحاسبية
# ------------------------------------------------------------
print("\n=== المحاسبة ===")

debit=x.execute("""
SELECT COALESCE(SUM(debit),0)
FROM journal_entry_lines
""").fetchone()[0]

credit=x.execute("""
SELECT COALESCE(SUM(credit),0)
FROM journal_entry_lines
""").fetchone()[0]

diff=round(float(debit)-float(credit),2)

check(
    "توازن القيود",
    abs(diff)<0.01,
    f"مدين={debit} | دائن={credit} | الفرق={diff}"
)

unbalanced=x.execute("""
SELECT je.id,je.entry_number,
       COALESCE(SUM(j.debit),0),
       COALESCE(SUM(j.credit),0)
FROM journal_entries je
JOIN journal_entry_lines j
ON j.journal_entry_id=je.id
GROUP BY je.id,je.entry_number
HAVING ABS(SUM(j.debit)-SUM(j.credit))>0.01
""").fetchall()

check(
    "القيود الفردية",
    len(unbalanced)==0,
    f"{len(unbalanced)} قيد غير متوازن"
)

print("عدد القيود:",x.execute(
    "SELECT COUNT(*) FROM journal_entries").fetchone()[0])
print("عدد أسطر القيود:",x.execute(
    "SELECT COUNT(*) FROM journal_entry_lines").fetchone()[0])

# ------------------------------------------------------------
# 4) الحسابات الرئيسية
# ------------------------------------------------------------
print("\n=== الحسابات الرئيسية ===")

for code,name in [
    ("1100","الخزينة"),
    ("1200","البنوك"),
    ("1300","العملاء"),
    ("1400","المخزون"),
    ("1410","ضريبة المدخلات"),
    ("2100","الموردون"),
    ("2200","ضريبة المخرجات"),
    ("3100","رأس المال"),
    ("4100","المبيعات"),
    ("5100","تكلفة البضاعة المباعة")
]:
    r=x.execute("""
    SELECT COALESCE(SUM(j.debit),0)-COALESCE(SUM(j.credit),0)
    FROM journal_entry_lines j
    JOIN accounts a ON a.id=j.account_id
    WHERE a.account_code=?
    """,(code,)).fetchone()[0]

    print(f"{code} | {name} | الرصيد: {round(float(r),2)}")

# ------------------------------------------------------------
# 5) المخزون
# ------------------------------------------------------------
print("\n=== المخزون ===")

stock=x.execute("""
SELECT
COUNT(*),
COALESCE(SUM(quantity),0),
COALESCE(SUM(quantity*average_cost),0),
COALESCE(SUM(reserved_quantity),0)
FROM stock
""").fetchone()

negative=x.execute("""
SELECT COUNT(*)
FROM stock
WHERE quantity<0 OR available_quantity<0
""").fetchone()[0]

check(
    "المخزون",
    negative==0,
    f"الأصناف={stock[0]} | الكمية={stock[1]} | القيمة={round(stock[2],2)}"
)

check(
    "المخزون المحاسبي",
    abs(float(stock[2])-616-100)<0.01,
    f"قيمة جدول المخزون={stock[2]}"
)

movements=x.execute("""
SELECT COUNT(*),
       COALESCE(SUM(CASE WHEN quantity>0 THEN quantity ELSE 0 END),0),
       COALESCE(SUM(CASE WHEN quantity<0 THEN ABS(quantity) ELSE 0 END),0)
FROM stock_movements
""").fetchone()

print("حركات المخزون:",movements[0])
print("إجمالي الوارد:",movements[1])
print("إجمالي الصادر:",movements[2])

# ------------------------------------------------------------
# 6) المبيعات
# ------------------------------------------------------------
print("\n=== المبيعات ===")

sales=x.execute("""
SELECT
COUNT(*),
COALESCE(SUM(subtotal),0),
COALESCE(SUM(tax_amount),0),
COALESCE(SUM(total_amount),0),
COALESCE(SUM(paid_amount),0),
COALESCE(SUM(due_amount),0)
FROM sales
WHERE status='POSTED'
""").fetchone()

print("الفواتير:",sales[0])
print("قبل الضريبة:",sales[1])
print("الضريبة:",sales[2])
print("الإجمالي:",sales[3])
print("المدفوع:",sales[4])
print("المتبقي:",sales[5])

sales_bad=x.execute("""
SELECT COUNT(*)
FROM sales
WHERE ABS(total_amount-(subtotal-discount_amount+tax_amount))>0.01
""").fetchone()[0]

check("حساب إجمالي المبيعات",sales_bad==0,f"{sales_bad} فواتير بها فرق")

sales_due=x.execute("""
SELECT COALESCE(SUM(due_amount),0)
FROM sales
WHERE status='POSTED'
""").fetchone()[0]

# ------------------------------------------------------------
# 7) المشتريات
# ------------------------------------------------------------
print("\n=== المشتريات ===")

purchases=x.execute("""
SELECT
COUNT(*),
COALESCE(SUM(subtotal),0),
COALESCE(SUM(tax_amount),0),
COALESCE(SUM(total_amount),0),
COALESCE(SUM(paid_amount),0),
COALESCE(SUM(due_amount),0)
FROM purchase_invoices
""").fetchone()

print("الفواتير:",purchases[0])
print("قبل الضريبة:",purchases[1])
print("الضريبة:",purchases[2])
print("الإجمالي:",purchases[3])
print("المدفوع:",purchases[4])
print("المتبقي:",purchases[5])

purchase_bad=x.execute("""
SELECT COUNT(*)
FROM purchase_invoices
WHERE ABS(total_amount-(subtotal+tax_amount))>0.01
""").fetchone()[0]

check("حساب إجمالي المشتريات",purchase_bad==0,
      f"{purchase_bad} فواتير بها فرق")

# ------------------------------------------------------------
# 8) العملاء
# ------------------------------------------------------------
print("\n=== العملاء ===")

customers=x.execute("""
SELECT COUNT(*),COALESCE(SUM(current_balance),0)
FROM customers
WHERE is_active=1
""").fetchone()

customer_tx=x.execute("""
SELECT COUNT(*),COALESCE(SUM(amount),0)
FROM customer_transactions
""").fetchone()

customer_pay=x.execute("""
SELECT COUNT(*),COALESCE(SUM(amount),0)
FROM customer_payments
""").fetchone()

print("العملاء:",customers[0])
print("أرصدة العملاء:",customers[1])
print("حركات العملاء:",customer_tx[0])
print("مدفوعات العملاء:",customer_pay[0])

# ------------------------------------------------------------
# 9) الموردون
# ------------------------------------------------------------
print("\n=== الموردون ===")

suppliers=x.execute("""
SELECT COUNT(*),COALESCE(SUM(current_balance),0)
FROM suppliers
WHERE is_active=1
""").fetchone()

supplier_tx=x.execute("""
SELECT COUNT(*),COALESCE(SUM(amount),0)
FROM supplier_transactions
""").fetchone()

print("الموردون:",suppliers[0])
print("أرصدة الموردين:",suppliers[1])
print("حركات الموردين:",supplier_tx[0])

# ------------------------------------------------------------
# 10) الضرائب
# ------------------------------------------------------------
print("\n=== الضرائب ===")

tax_input=x.execute("""
SELECT COALESCE(SUM(debit),0)-COALESCE(SUM(credit),0)
FROM journal_entry_lines j
JOIN accounts a ON a.id=j.account_id
WHERE a.account_code='1410'
""").fetchone()[0]

tax_output=x.execute("""
SELECT COALESCE(SUM(credit),0)-COALESCE(SUM(debit),0)
FROM journal_entry_lines j
JOIN accounts a ON a.id=j.account_id
WHERE a.account_code='2200'
""").fetchone()[0]

print("ضريبة المدخلات:",tax_input)
print("ضريبة المخرجات:",tax_output)
print("صافي الضريبة:",round(float(tax_output)-float(tax_input),2))

# ------------------------------------------------------------
# 11) المنتجات
# ------------------------------------------------------------
print("\n=== المنتجات ===")

products=x.execute("""
SELECT
COUNT(*),
COALESCE(SUM(CASE WHEN cost_price<0 THEN 1 ELSE 0 END),0),
COALESCE(SUM(CASE WHEN sale_price<0 THEN 1 ELSE 0 END),0)
FROM products
""").fetchone()

print("المنتجات:",products[0])

check(
    "أسعار المنتجات",
    products[1]==0 and products[2]==0,
    f"تكلفة سالبة={products[1]} | بيع سالب={products[2]}"
)

# ------------------------------------------------------------
# 12) نسخ الاحتياط
# ------------------------------------------------------------
print("\n=== النسخ الاحتياطية ===")

import os

backup_dir=r"database\backups"

if os.path.exists(backup_dir):
    backups=[
        f for f in os.listdir(backup_dir)
        if f.lower().endswith(".db")
    ]
else:
    backups=[]

print("عدد النسخ الاحتياطية:",len(backups))

# ------------------------------------------------------------
# النتيجة النهائية
# ------------------------------------------------------------
print("\n"+"="*75)
print("                 النتيجة النهائية")
print("="*75)

print("تحذيرات:",len(warnings))
print("أخطاء العلاقات:",len(fk))
print("فرق المحاسبة:",diff)
print("عدد القيود غير المتوازنة:",len(unbalanced))
print("عدد فواتير المبيعات ذات الفرق:",sales_bad)
print("عدد فواتير المشتريات ذات الفرق:",purchase_bad)
print("أرصدة مخزون سالبة:",negative)

if not warnings and not fk and abs(diff)<0.01 and len(unbalanced)==0 \
   and sales_bad==0 and purchase_bad==0 and negative==0:
    print("\nالحالة العامة: ممتازة - لا توجد مشكلة أساسية مكتشفة")
else:
    print("\nالحالة العامة: توجد نقاط تحتاج مراجعة")
    if warnings:
        print("\n=== تفاصيل التحذيرات ===")
        for n,d in warnings:
            print("-",n,":",d)

print("="*75)

c.close()
