import sqlite3
from pathlib import Path

DB=Path("database/nizam_alqirtasiyah.db")
con=sqlite3.connect(DB)
con.execute("PRAGMA foreign_keys=ON")
c=con.cursor()

def cols(t):
    return {r[1] for r in c.execute(f'PRAGMA table_info("{t}")')}

def insert(t,data):
    available=cols(t)
    data={k:v for k,v in data.items() if k in available}
    names=",".join(data)
    marks=",".join(["?"]*len(data))
    c.execute(f'INSERT INTO "{t}" ({names}) VALUES ({marks})',tuple(data.values()))
    return c.lastrowid

company=c.execute("SELECT id FROM companies LIMIT 1").fetchone()
if not company:
    company=(insert("companies",{"name":"قرطاسية لؤلؤة الأربعين النموذجية","tax_number":"000000000000003"}),)

branch=c.execute("SELECT id FROM branches LIMIT 1").fetchone()
if not branch:
    branch=(insert("branches",{"company_id":company[0],"name":"الفرع الرئيسي"}),)

warehouse=c.execute("SELECT id FROM warehouses LIMIT 1").fetchone()
if not warehouse:
    warehouse=(insert("warehouses",{"branch_id":branch[0],"name":"المستودع الرئيسي","code":"MAIN-WH"}),)

supplier=c.execute("SELECT id FROM suppliers LIMIT 1").fetchone()
if not supplier:
    supplier=(insert("suppliers",{
        "supplier_code":"SUP-001",
        "name":"مورد الاختبار",
        "name_ar":"مورد الاختبار",
        "is_active":1
    }),)

product=c.execute("SELECT id FROM products LIMIT 1").fetchone()
if not product:
    category=c.execute("SELECT id FROM product_categories LIMIT 1").fetchone()
    unit=c.execute("SELECT id FROM units LIMIT 1").fetchone()
    product=(insert("products",{
        "sku":"TEST-001",
        "name_ar":"منتج اختبار ERP",
        "category_id":category[0] if category else None,
        "unit_id":unit[0] if unit else None,
        "cost_price":10,
        "sale_price":23,
        "is_active":1
    }),)

con.commit()
print("COMPANY:",company[0])
print("BRANCH:",branch[0])
print("WAREHOUSE:",warehouse[0])
print("SUPPLIER:",supplier[0])
print("PRODUCT:",product[0])
print("STATUS: OPERATIONAL SEED SUCCESS")
con.close()
