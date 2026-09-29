import sqlite3,datetime,shutil
from pathlib import Path

ROOT=Path.cwd()
DB=ROOT/"database/nizam_alqirtasiyah.db"
BACK=ROOT/"backups"
ts=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup=BACK/f"before_master_data_fill_{ts}.db"
shutil.copy2(DB,backup)

con=sqlite3.connect(DB)
cur=con.cursor()

def columns(table):
    return [r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()]

def exists(table):
    return bool(cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)
    ).fetchone())

def insert_dynamic(table,data,unique_col=None):
    if not exists(table):
        return False
    cols=columns(table)
    data={k:v for k,v in data.items() if k in cols}
    if not data:
        return False
    if unique_col and unique_col in cols:
        if cur.execute(f"SELECT 1 FROM {table} WHERE {unique_col}=?",(data.get(unique_col),)).fetchone():
            return False
    names=list(data)
    vals=[data[x] for x in names]
    marks=",".join("?" for _ in names)
    cur.execute(
        f"INSERT INTO {table} ({','.join(names)}) VALUES ({marks})",
        vals
    )
    return True

# -------------------------------------------------
# الشركة والفرع والمستودع
# -------------------------------------------------
if exists("companies"):
    insert_dynamic("companies",{
        "name":"قرطاسية لؤلؤة الأربعين النموذجية",
        "tax_number":"",
        "phone":"",
        "address":"حي الصفا، شارع عبدالله بن سهل، جدة 23456"
    },"name")

if exists("branches"):
    insert_dynamic("branches",{
        "name":"الفرع الرئيسي",
        "branch_code":"BR-001","code":"BR-001",
        "company_id":1,
        "is_active":1
    },"branch_code")

if exists("warehouses"):
    insert_dynamic("warehouses",{
        "name":"المستودع الرئيسي",
        "code":"WH-001",
        "branch_id":1,
        "is_active":1
    },"code")

# -------------------------------------------------
# التصنيفات
# -------------------------------------------------
categories=[
("CAT-001","أدوات الكتابة"),
("CAT-002","الدفاتر والملفات"),
("CAT-003","الرسم والفنون"),
("CAT-004","مستلزمات مدرسية"),
("CAT-005","مستلزمات مكتبية"),
("CAT-006","الطباعة والخدمات"),
("CAT-007","الإلكترونيات والملحقات"),
("CAT-008","الهدايا"),
("CAT-009","الأحبار والطابعات"),
("CAT-010","الألعاب التعليمية")
]

if exists("product_categories"):
    cc=columns("product_categories")
    for code,name in categories:
        d={}
        if "code" in cc:d["code"]=code
        if "category_code" in cc:d["category_code"]=code
        if "name" in cc:d["name"]=name
        if "name_ar" in cc:d["name_ar"]=name
        if "is_active" in cc:d["is_active"]=1
        if d:
            key="code" if "code" in cc else ("category_code" if "category_code" in cc else None)
            insert_dynamic("product_categories",d,key)

# -------------------------------------------------
# العلامات التجارية
# -------------------------------------------------
brands=[
("BRD-001","BIC"),
("BRD-002","Pilot"),
("BRD-003","Staedtler"),
("BRD-004","Faber-Castell"),
("BRD-005","HP"),
("BRD-006","Canon"),
("BRD-007","A4"),
("BRD-008","Maped")
]

if exists("brands"):
    bc=columns("brands")
    for code,name in brands:
        d={}
        if "code" in bc:d["code"]=code
        if "brand_code" in bc:d["brand_code"]=code
        if "name" in bc:d["name"]=name
        if "name_ar" in bc:d["name_ar"]=name
        if "is_active" in bc:d["is_active"]=1
        key="code" if "code" in bc else ("brand_code" if "brand_code" in bc else None)
        insert_dynamic("brands",d,key)

# -------------------------------------------------
# الوحدات
# -------------------------------------------------
units=[
("PCS","قطعة"),
("BOX","علبة"),
("PACK","حزمة"),
("DOZEN","درزن"),
("SET","طقم"),
("SERVICE","خدمة")
]

if exists("units"):
    uc=columns("units")
    for code,name in units:
        d={}
        if "code" in uc:d["code"]=code
        if "unit_code" in uc:d["unit_code"]=code
        if "name" in uc:d["name"]=name
        if "name_ar" in uc:d["name_ar"]=name
        if "is_active" in uc:d["is_active"]=1
        key="code" if "code" in uc else ("unit_code" if "unit_code" in uc else None)
        insert_dynamic("units",d,key)

# -------------------------------------------------
# المنتجات
# -------------------------------------------------
products=[
("PEN-BLU","قلم حبر أزرق","BIC",1.50,2.00),
("PEN-BLK","قلم حبر أسود","BIC",1.50,2.00),
("PEN-RED","قلم حبر أحمر","Pilot",1.50,2.00),
("PEN-GEL","قلم جل","Pilot",2.50,4.00),
("PENCIL-HB","قلم رصاص HB","Staedtler",1.00,1.50),
("ERASER","ممحاة مدرسية","Faber-Castell",1.00,1.50),
("SHARPENER","براية","Maped",1.50,2.50),
("NOTE-A5","دفتر A5","A4",4.00,6.00),
("NOTE-A4","دفتر A4","A4",7.00,10.00),
("FILE-A4","ملف A4","A4",2.50,4.00),
("RULER-30","مسطرة 30 سم","Maped",2.00,3.50),
("COLOR-12","ألوان خشبية 12 لون","Faber-Castell",12.00,18.00),
("MARKER","أقلام تحديد","BIC",5.00,8.00),
("PAPER-A4","ورق تصوير A4","HP",15.00,22.00),
("INK-BLACK","حبر طابعة أسود","HP",35.00,50.00),
("USB-32","ذاكرة USB 32GB","HP",18.00,28.00),
("CALCULATOR","آلة حاسبة مدرسية","Canon",20.00,30.00),
("GLUE","صمغ مدرسي","Maped",3.00,5.00),
("SCISSORS","مقص مدرسي","Maped",4.00,7.00),
("PRINT-BW","طباعة أبيض وأسود","",0.20,0.50)
]

if exists("products"):
    pc=columns("products")
    # نأخذ أول تصنيف/علامة/وحدة موجودة فعليًا
    cat=cur.execute("SELECT id FROM product_categories ORDER BY id LIMIT 1").fetchone()
    brand=cur.execute("SELECT id FROM brands ORDER BY id LIMIT 1").fetchone()
    unit=cur.execute("SELECT id FROM units ORDER BY id LIMIT 1").fetchone()

    for sku,name,brand_name,cost,sale in products:
        if cur.execute("SELECT 1 FROM products WHERE sku=?",(sku,)).fetchone():
            continue
        d={}
        if "sku" in pc:d["sku"]=sku
        if "name_ar" in pc:d["name_ar"]=name
        if "name" in pc:d["name"]=name
        if "cost_price" in pc:d["cost_price"]=cost
        if "sale_price" in pc:d["sale_price"]=sale
        if "wholesale_price" in pc:d["wholesale_price"]=round(sale*0.90,2)
        if "school_price" in pc:d["school_price"]=round(sale*0.92,2)
        if "min_price" in pc:d["min_price"]=sale
        if "reorder_point" in pc:d["reorder_point"]=5
        if "min_stock" in pc:d["min_stock"]=5
        if "max_stock" in pc:d["max_stock"]=100
        if "is_active" in pc:d["is_active"]=1
        if cat and "category_id" in pc:d["category_id"]=cat[0]
        if brand and "brand_id" in pc:d["brand_id"]=brand[0]
        if unit and "unit_id" in pc:d["unit_id"]=unit[0]
        if "product_type" in pc:d["product_type"]="SERVICE" if sku=="PRINT-BW" else "PRODUCT"
        insert_dynamic("products",d,"sku")

# -------------------------------------------------
# العملاء
# -------------------------------------------------
customers=[
("CUS-001","مدرسة اليقظة","ORGANIZATION"),
("CUS-002","مدرسة الأمل","ORGANIZATION"),
("CUS-003","جامعة خاصة","ORGANIZATION"),
("CUS-004","محمد أحمد","INDIVIDUAL"),
("CUS-005","أحمد علي","INDIVIDUAL"),
("CUS-006","مكتبة التعاون","BUSINESS"),
("CUS-007","مدرسة المستقبل","ORGANIZATION"),
("CUS-008","شركة خدمات تعليمية","BUSINESS"),
("CUS-009","عبدالله محمد","INDIVIDUAL"),
("CUS-010","سارة أحمد","INDIVIDUAL")
]

if exists("customers"):
    for code,name,typ in customers:
        insert_dynamic("customers",{
            "customer_code":code,"name":name,"customer_type":typ,
            "current_balance":0,"opening_balance":0,
            "credit_limit":5000,"is_active":1
        },"customer_code")

# -------------------------------------------------
# الموردون
# -------------------------------------------------
suppliers=[
("SUP-001","مؤسسة الخليج للقرطاسية"),
("SUP-002","شركة الأدوات المدرسية"),
("SUP-003","مورد الأحبار والطابعات"),
("SUP-004","مؤسسة الورق الحديثة"),
("SUP-005","شركة التقنية المكتبية"),
("SUP-006","مورد الأدوات الفنية"),
("SUP-007","مؤسسة الجملة التعليمية"),
("SUP-008","شركة المستلزمات المكتبية")
]

if exists("suppliers"):
    for code,name in suppliers:
        insert_dynamic("suppliers",{
            "supplier_code":code,"name":name,
            "supplier_type":"BUSINESS",
            "current_balance":0,
            "credit_limit":10000,
            "is_active":1
        },"supplier_code")

# -------------------------------------------------
# الحسابات الأساسية
# -------------------------------------------------
accounts=[
("1000","الأصول","asset"),
("1100","الخزينة","asset"),
("1200","البنوك","asset"),
("1300","العملاء","asset"),
("1400","المخزون","asset"),
("1410","ضريبة القيمة المضافة - مدخلات","asset"),
("2000","الخصوم","liability"),
("2100","الموردون","liability"),
("2200","ضريبة القيمة المضافة - مخرجات","liability"),
("4000","الإيرادات","revenue"),
("4100","مبيعات القرطاسية","revenue"),
("4200","خدمات الطباعة","revenue"),
("5000","المصروفات","expense"),
("5100","تكلفة البضاعة المباعة","expense"),
("5200","مصروفات تشغيلية","expense"),
("5300","مصروفات رواتب","expense")
]

if exists("accounts"):
    for code,name,typ in accounts:
        insert_dynamic("accounts",{
            "account_code":code,
            "account_name":name,
            "account_type":typ,
            "is_active":1,
            "allow_posting":1,
            "opening_balance":0
        },"account_code")

# -------------------------------------------------
# الضريبة
# -------------------------------------------------
if exists("tax_rates"):
    insert_dynamic("tax_rates",{
        "code":"VAT15",
        "name":"ضريبة القيمة المضافة 15%",
        "rate":15,
        "is_active":1
    },"code")

con.commit()

integrity=cur.execute("PRAGMA integrity_check").fetchone()[0]
fk=cur.execute("PRAGMA foreign_key_check").fetchall()

tables=[
"companies","branches","warehouses","product_categories","brands","units",
"products","customers","suppliers","accounts","tax_rates","users",
"sales","sale_items","purchase_orders","purchase_invoices",
"stock_movements","cash_receipts","cash_payments",
"journal_entries","journal_entry_lines","e_invoices"
]

print("="*85)
print("MASTER DATA FILL")
print("="*85)
print("BACKUP:",backup)

for t in tables:
    if exists(t):
        print(f"{t:28} {cur.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]}")

print("-"*85)
print("INTEGRITY:",integrity)
print("FOREIGN KEY ERRORS:",len(fk))
print("STATUS: SUCCESS" if integrity=="ok" and not fk else "STATUS: FAILED")
print("="*85)

con.close()


