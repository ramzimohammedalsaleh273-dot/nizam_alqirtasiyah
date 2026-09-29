import sqlite3, os, shutil, datetime, json, hashlib

DB = "database/nizam_alqirtasiyah.db"
os.makedirs("backups", exist_ok=True)

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = f"backups/before_arabic_operational_data_{stamp}.db"
shutil.copy2(DB, backup)

con = sqlite3.connect(DB)
con.execute("PRAGMA foreign_keys=ON")
con.execute("PRAGMA journal_mode=WAL")
cur = con.cursor()

print("="*80)
print("نظام القرطاسية — تعبئة البيانات التشغيلية العربية")
print("="*80)
print("BACKUP:", backup)

def cols(table):
    return {r[1] for r in cur.execute(f'PRAGMA table_info("{table}")')}

def exists(table):
    return cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,)
    ).fetchone() is not None

def update_id(table, row_id, data):
    if not exists(table):
        return
    c = cols(table)
    data = {k:v for k,v in data.items() if k in c}
    if not data:
        return
    sets = ", ".join(f'"{k}"=?' for k in data)
    cur.execute(
        f'UPDATE "{table}" SET {sets} WHERE id=?',
        tuple(data.values()) + (row_id,)
    )

def insert_row(table, data):
    if not exists(table):
        return None
    c = cols(table)
    data = {k:v for k,v in data.items() if k in c}
    if not data:
        return None
    keys = list(data)
    marks = ",".join("?" for _ in keys)
    cur.execute(
        f'INSERT INTO "{table}" ({",".join(chr(34)+k+chr(34) for k in keys)}) VALUES ({marks})',
        tuple(data[k] for k in keys)
    )
    return cur.lastrowid

def upsert_by_id(table, row_id, data):
    if not exists(table):
        return
    n = cur.execute(
        f'SELECT COUNT(*) FROM "{table}" WHERE id=?',(row_id,)
    ).fetchone()[0]
    if n:
        update_id(table,row_id,data)
    else:
        data = dict(data)
        if "id" in cols(table):
            data["id"] = row_id
        insert_row(table,data)

def set_if_exists(table, row_id, data):
    try:
        update_id(table,row_id,data)
    except Exception as e:
        print("WARN", table, row_id, e)

# ------------------------------------------------------------------
# الشركة والفرع والمستودع
# ------------------------------------------------------------------
if exists("companies"):
    upsert_by_id("companies",1,{
        "name":"قرطاسية لؤلؤة الأربعين النموذجية",
        "phone":"",
        "email":"",
        "address":"حي الصفا، شارع عبدالله بن سهل",
        "country":"المملكة العربية السعودية",
        "city":"جدة",
        "currency_code":"SAR",
        "is_active":1
    })

if exists("branches"):
    upsert_by_id("branches",1,{
        "company_id":1,
        "name":"الفرع الرئيسي",
        "code":"BR-001",
        "phone":"",
        "address":"حي الصفا، شارع عبدالله بن سهل، جدة",
        "is_active":1
    })

if exists("warehouses"):
    upsert_by_id("warehouses",1,{
        "branch_id":1,
        "name":"المستودع الرئيسي",
        "code":"WH-001",
        "warehouse_type":"MAIN",
        "is_active":1
    })

# ------------------------------------------------------------------
# الأقسام
# ------------------------------------------------------------------
departments = [
    "الإدارة",
    "المبيعات",
    "المشتريات",
    "المخزون والمستودعات",
    "المحاسبة والمالية",
    "خدمة العملاء",
    "الطباعة والتصوير",
]

if exists("departments"):
    for i,name in enumerate(departments,1):
        upsert_by_id("departments",i,{"name":name,"is_active":1})

# ------------------------------------------------------------------
# الوظائف
# ------------------------------------------------------------------
positions = [
    ("مدير الفرع",1,7000),
    ("محاسب",5,5000),
    ("أمين مستودع",4,4000),
    ("بائع",2,3500),
    ("موظف خدمة عملاء",6,3500),
    ("موظف طباعة وتصوير",7,3500),
    ("مساعد مبيعات",2,3000),
]

if exists("job_positions"):
    for i,(name,dept,salary) in enumerate(positions,1):
        upsert_by_id("job_positions",i,{
            "name":name,
            "department_id":dept,
            "base_salary":salary,
            "is_active":1
        })

# ------------------------------------------------------------------
# الموظفون
# ------------------------------------------------------------------
employees = [
    ("EMP-001","مدير الفرع","0500000001","",1,1,"2026-01-01",7000),
    ("EMP-002","محاسب الفرع","0500000002","",5,2,"2026-01-01",5000),
    ("EMP-003","أمين المستودع","0500000003","",4,3,"2026-01-01",4000),
    ("EMP-004","موظف مبيعات","0500000004","",2,4,"2026-01-01",3500),
    ("EMP-005","موظف خدمة العملاء","0500000005","",6,5,"2026-01-01",3500),
    ("EMP-006","موظف الطباعة والتصوير","0500000006","",7,6,"2026-01-01",3500),
]

if exists("employees"):
    for i,(eno,name,phone,email,dept,pos,date,salary) in enumerate(employees,1):
        upsert_by_id("employees",i,{
            "employee_no":eno,
            "full_name":name,
            "phone":phone,
            "email":email,
            "department_id":dept,
            "position_id":pos,
            "hire_date":date,
            "status":"ACTIVE",
            "basic_salary":salary
        })

# ------------------------------------------------------------------
# الوحدات
# ------------------------------------------------------------------
units = [
    ("قطعة","قطعة"),
    ("علبة","علبة"),
    ("باكيت","باكيت"),
    ("كرتون","كرتون"),
    ("دفتر","دفتر"),
    ("مجلد","مجلد"),
    ("متر","م"),
    ("خدمة","خدمة"),
]

if exists("units"):
    for i,(name,symbol) in enumerate(units,1):
        upsert_by_id("units",i,{
            "name":name,
            "symbol":symbol,
            "is_active":1
        })

# ------------------------------------------------------------------
# التصنيفات
# ------------------------------------------------------------------
categories = [
    ("أدوات الكتابة","CAT-01"),
    ("الدفاتر والكراسات","CAT-02"),
    ("الرسم والتلوين","CAT-03"),
    ("الورق","CAT-04"),
    ("الملفات والمجلدات","CAT-05"),
    ("الأدوات الهندسية","CAT-06"),
    ("المستلزمات المدرسية","CAT-07"),
    ("القرطاسية المكتبية","CAT-08"),
    ("الطباعة والتصوير","CAT-09"),
    ("الأحبار ومستلزمات الطباعة","CAT-10"),
    ("المستلزمات التقنية","CAT-11"),
    ("الهدايا","CAT-12"),
    ("الحقائب","CAT-13"),
    ("مستلزمات الجامعة","CAT-14"),
]

if exists("product_categories"):
    for i,(name,code) in enumerate(categories,1):
        upsert_by_id("product_categories",i,{
            "parent_id":None,
            "name":name,
            "code":code,
            "description":name,
            "is_active":1
        })

# ------------------------------------------------------------------
# الماركات
# ------------------------------------------------------------------
brands = [
    "بيك",
    "فابر كاستل",
    "ستابلر",
    "مابيد",
    "بنتل",
    "ساکورا",
    "ماركة لؤلؤة",
]

if exists("brands"):
    for i,name in enumerate(brands,1):
        upsert_by_id("brands",i,{
            "name":name,
            "description":"منتجات قرطاسية",
            "is_active":1
        })

# ------------------------------------------------------------------
# المنتجات — 31 منتجًا عربيًا
# ------------------------------------------------------------------
products = [
("PEN-001","قلم جاف أزرق","أدوات الكتابة",1,1,2.00,3.00,2.70,2.60,2.50),
("PEN-002","قلم جاف أسود","أدوات الكتابة",1,1,2.00,3.00,2.70,2.60,2.50),
("PEN-003","قلم جاف أحمر","أدوات الكتابة",1,1,2.00,3.00,2.70,2.60,2.50),
("PEN-004","قلم رصاص HB","أدوات الكتابة",1,2,1.50,2.50,2.20,2.10,2.00),
("PEN-005","قلم رصاص 2B","أدوات الكتابة",1,2,1.50,2.50,2.20,2.10,2.00),
("PEN-006","قلم تحديد أصفر","أدوات الكتابة",1,3,2.50,4.00,3.60,3.50,3.30),
("NB-001","دفتر 100 ورقة مسطر","الدفاتر والكراسات",2,7,8.00,12.00,10.50,10.00,9.50),
("NB-002","دفتر 200 ورقة مسطر","الدفاتر والكراسات",2,7,14.00,20.00,18.00,17.00,16.00),
("NB-003","كراسة 60 ورقة","الدفاتر والكراسات",2,7,4.00,7.00,6.00,5.80,5.50),
("NB-004","دفتر رسم","الرسم والتلوين",2,4,6.00,10.00,9.00,8.50,8.00),
("ART-001","علبة ألوان خشبية 12 لون","الرسم والتلوين",3,2,8.00,14.00,12.50,12.00,11.00),
("ART-002","ألوان شمعية 12 لون","الرسم والتلوين",3,2,6.00,10.00,9.00,8.50,8.00),
("ART-003","ألوان مائية","الرسم والتلوين",3,4,7.00,12.00,10.50,10.00,9.50),
("PAPER-001","ورق تصوير A4 أبيض 80 جرام","الورق",4,7,14.00,22.00,20.00,19.00,18.00),
("PAPER-002","ورق ملون A4","الورق",4,7,12.00,20.00,18.00,17.00,16.00),
("FILE-001","ملف بلاستيكي شفاف","الملفات والمجلدات",5,7,1.50,3.00,2.50,2.30,2.00),
("FILE-002","مجلد حلقي","الملفات والمجلدات",5,7,6.00,10.00,9.00,8.50,8.00),
("GEO-001","مسطرة 30 سم","الأدوات الهندسية",6,4,1.50,3.00,2.50,2.30,2.00),
("GEO-002","طقم هندسي","الأدوات الهندسية",6,4,5.00,9.00,8.00,7.50,7.00),
("SCHOOL-001","ممحاة بيضاء","المستلزمات المدرسية",7,2,1.00,2.00,1.70,1.60,1.50),
("SCHOOL-002","براية معدنية","المستلزمات المدرسية",7,3,2.00,4.00,3.50,3.30,3.00),
("SCHOOL-003","مقص مدرسي","المستلزمات المدرسية",7,4,3.50,6.00,5.50,5.00,4.50),
("OFFICE-001","دباسة مكتبية","القرطاسية المكتبية",8,3,8.00,14.00,12.50,12.00,11.00),
("OFFICE-002","علبة دبابيس دباسة","القرطاسية المكتبية",8,3,2.00,4.00,3.50,3.20,3.00),
("OFFICE-003","شريط لاصق","القرطاسية المكتبية",8,7,2.00,4.00,3.50,3.20,3.00),
("INK-001","حبر طابعة أسود","الأحبار ومستلزمات الطباعة",10,7,35.00,55.00,50.00,48.00,45.00),
("INK-002","حبر طابعة ملون","الأحبار ومستلزمات الطباعة",10,7,40.00,65.00,58.00,55.00,52.00),
("BAG-001","حقيبة مدرسية","الحقائب",13,7,45.00,70.00,65.00,60.00,55.00),
("TECH-001","ذاكرة USB سعة 32 جيجابايت","المستلزمات التقنية",11,7,18.00,30.00,27.00,25.00,23.00),
("UNIV-001","دفتر جامعي 200 ورقة","مستلزمات الجامعة",14,7,15.00,23.00,21.00,20.00,18.00),
("OFFICE-004","آلة حاسبة مكتبية","القرطاسية المكتبية",8,4,18.00,30.00,27.00,25.00,23.00),
]

if exists("products"):
    pc = cols("products")
    for i,p in enumerate(products,1):
        sku,name,cat,unit,brand,cost,sale,wholesale,school,corporate = p
        upsert_by_id("products",i,{
            "sku":sku,
            "name_ar":name,
            "name_en":name,
            "category_id":categories.index((cat,next(x[1] for x in categories if x[0]==cat)))+1 if False else next(j for j,x in enumerate(categories,1) if x[0]==cat),
            "brand_id":brand,
            "unit_id":unit,
            "product_type":"PRODUCT",
            "description":name,
            "cost_price":cost,
            "sale_price":sale,
            "wholesale_price":wholesale,
            "school_price":school,
            "corporate_price":corporate,
            "min_price":sale,
            "reorder_point":5,
            "min_stock":5,
            "max_stock":100,
            "is_active":1
        })

# ------------------------------------------------------------------
# باركود لكل منتج
# ------------------------------------------------------------------
if exists("product_barcodes"):
    for i in range(1,len(products)+1):
        barcode = f"628000000{i:03d}"
        row = cur.execute(
            "SELECT id FROM product_barcodes WHERE product_id=? AND is_primary=1",
            (i,)
        ).fetchone()
        if row:
            update_id("product_barcodes",row[0],{
                "product_id":i,
                "barcode":barcode,
                "is_primary":1
            })
        else:
            insert_row("product_barcodes",{
                "product_id":i,
                "barcode":barcode,
                "is_primary":1
            })

# ------------------------------------------------------------------
# العملاء
# ------------------------------------------------------------------
customer_groups = [
    ("عملاء أفراد",0,"RETAIL"),
    ("طلاب",5,"SCHOOL"),
    ("مدارس",10,"SCHOOL"),
    ("شركات ومؤسسات",8,"CORPORATE"),
]

if exists("customer_groups"):
    for i,(name,disc,ptype) in enumerate(customer_groups,1):
        upsert_by_id("customer_groups",i,{
            "name":name,
            "discount_percent":disc,
            "price_type":ptype,
            "is_active":1
        })

customers = [
"عميل نقدي",
"مدرسة اليقظة",
"مدرسة الإبداع الأهلية",
"مدرسة النخبة",
"جامعة الملك عبدالعزيز",
"شركة الإمداد المكتبي",
"مؤسسة رواد التعليم",
"مكتبة الطالب",
"مدارس المستقبل",
"مؤسسة الصفوة",
]

if exists("customers"):
    for i,name in enumerate(customers,1):
        upsert_by_id("customers",i,{
            "customer_code":f"CUS-{i:03d}",
            "name":name,
            "customer_type":"RETAIL" if i==1 else "CORPORATE",
            "group_id":1 if i==1 else (3 if i in [2,3,4,9] else 4),
            "phone":f"050000{1000+i:04d}",
            "email":"",
            "tax_number":"",
            "credit_limit":0 if i==1 else 5000,
            "opening_balance":0,
            "current_balance":0,
            "is_active":1
        })

# ------------------------------------------------------------------
# مجموعات الموردين والموردون
# ------------------------------------------------------------------
supplier_groups = [
    ("موردو القرطاسية","موردو الأدوات والقرطاسية"),
    ("موردو التقنية والطباعة","موردو التقنية والأحبار"),
]

if exists("supplier_groups"):
    for i,(name,desc) in enumerate(supplier_groups,1):
        upsert_by_id("supplier_groups",i,{
            "name":name,
            "description":desc
        })

suppliers = [
"شركة المورد الأول للقرطاسية",
"مؤسسة الإمداد المدرسي",
"شركة الورق المتحدة",
"مؤسسة أدوات التعليم",
"شركة الأحبار والطباعة",
"مؤسسة الحقائب المدرسية",
"شركة التقنية المكتبية",
"مؤسسة اللوازم المكتبية",
"شركة القرطاسية الحديثة",
"مؤسسة تجهيز المدارس",
]

if exists("suppliers"):
    for i,name in enumerate(suppliers,1):
        upsert_by_id("suppliers",i,{
            "supplier_code":f"SUP-{i:03d}",
            "name":name,
            "supplier_type":"LOCAL",
            "phone":f"055000{1000+i:04d}",
            "email":"",
            "tax_number":"",
            "address":"المملكة العربية السعودية",
            "credit_limit":10000,
            "current_balance":0,
            "group_id":1 if i<=5 else 2,
            "is_active":1
        })

# ------------------------------------------------------------------
# الحسابات الرئيسية
# ------------------------------------------------------------------
accounts = [
("1100","الخزينة","ASSET"),
("1200","البنوك","ASSET"),
("1300","العملاء","ASSET"),
("1400","المخزون","ASSET"),
("1410","ضريبة القيمة المضافة - مدخلات","ASSET"),
("1500","الأصول الثابتة","ASSET"),
("2100","الموردون","LIABILITY"),
("2200","ضريبة القيمة المضافة - مخرجات","LIABILITY"),
("3100","رأس المال","EQUITY"),
("4100","مبيعات القرطاسية","REVENUE"),
("4200","إيرادات الطباعة والتصوير","REVENUE"),
("4300","إيرادات الخدمات","REVENUE"),
("5100","تكلفة البضاعة المباعة","EXPENSE"),
("5200","مصروفات الرواتب","EXPENSE"),
("5300","مصروفات الكهرباء والمياه","EXPENSE"),
("5400","مصروفات الإيجار","EXPENSE"),
("5500","مصروفات التشغيل","EXPENSE"),
]

if exists("accounts"):
    for i,(code,name,atype) in enumerate(accounts,1):
        upsert_by_id("accounts",i,{
            "account_code":code,
            "account_name":name,
            "account_type":atype,
            "is_active":1,
            "allow_posting":1,
            "opening_balance":0
        })

# ------------------------------------------------------------------
# دليل الحسابات الآخر
# ------------------------------------------------------------------
if exists("chart_of_accounts"):
    for i,(code,name,atype) in enumerate(accounts,1):
        at = {
            "ASSET":1,
            "LIABILITY":2,
            "EQUITY":3,
            "REVENUE":4,
            "EXPENSE":5
        }.get(atype,1)
        upsert_by_id("chart_of_accounts",i,{
            "code":code,
            "name":name,
            "account_type_id":at,
            "parent_id":None,
            "level":1,
            "is_group":0,
            "is_active":1
        })

# ------------------------------------------------------------------
# البنك
# ------------------------------------------------------------------
if exists("banks"):
    upsert_by_id("banks",1,{
        "name":"البنك الرئيسي",
        "code":"BANK-001",
        "is_active":1
    })

if exists("bank_accounts"):
    upsert_by_id("bank_accounts",1,{
        "bank_id":1,
        "branch_id":1,
        "account_name":"الحساب البنكي الرئيسي",
        "account_number":"",
        "iban":"",
        "currency_code":"SAR",
        "opening_balance":0,
        "current_balance":0,
        "is_active":1
    })

# ------------------------------------------------------------------
# الخزينة
# ------------------------------------------------------------------
if exists("cash_registers"):
    upsert_by_id("cash_registers",1,{
        "branch_id":1,
        "name":"الخزينة الرئيسية",
        "code":"CASH-001",
        "is_active":1
    })

if exists("cash_sessions"):
    row = cur.execute("SELECT id FROM cash_sessions WHERE id=1").fetchone()
    if row:
        update_id("cash_sessions",1,{
            "register_id":1,
            "user_id":1,
            "opening_balance":0,
            "expected_balance":0,
            "actual_balance":0,
            "difference":0,
            "status":"OPEN"
        })

# ------------------------------------------------------------------
# الضرائب
# ------------------------------------------------------------------
if exists("tax_rates"):
    taxes = [
        (1,"VAT15","ضريبة القيمة المضافة 15%",15),
        (2,"VAT0","ضريبة صفرية",0),
        (3,"EXEMPT","معفى من الضريبة",0),
    ]
    for i,code,name,rate in taxes:
        upsert_by_id("tax_rates",i,{
            "code":code,
            "name":name,
            "rate":rate,
            "is_active":1
        })

if exists("tax_config"):
    update_id("tax_config",1,{
        "vat_rate":15,
        "currency":"SAR",
        "country_code":"SA",
        "invoice_prefix":"INV",
        "is_active":1
    })

# ------------------------------------------------------------------
# العملة
# ------------------------------------------------------------------
if exists("currencies"):
    upsert_by_id("currencies",1,{
        "code":"SAR",
        "name":"الريال السعودي",
        "symbol":"ر.س",
        "decimal_places":2,
        "is_base":1,
        "is_active":1
    })

# ------------------------------------------------------------------
# خدمات الطباعة
# ------------------------------------------------------------------
services = [
("PRINT-A4-BW","تصوير ورق A4 أبيض وأسود","تصوير","ورقة",0.50),
("PRINT-A4-COLOR","تصوير ورق A4 ملون","تصوير","ورقة",2.00),
("PRINT-A4","طباعة A4","طباعة","ورقة",1.00),
("BIND","تجليد حراري","تجليد","خدمة",8.00),
("SCAN","مسح ضوئي","مسح","صفحة",1.00),
]

if exists("printing_services"):
    for i,(code,name,typ,unit,price) in enumerate(services,1):
        upsert_by_id("printing_services",i,{
            "code":code,
            "name":name,
            "service_type":typ,
            "unit":unit,
            "base_price":price,
            "tax_rate":15,
            "is_active":1
        })

# ------------------------------------------------------------------
# الإعدادات العربية
# ------------------------------------------------------------------
settings = [
("company_name","قرطاسية لؤلؤة الأربعين النموذجية","text","اسم المنشأة"),
("system_name","نظام القرطاسية","text","اسم النظام"),
("language","العربية","text","لغة النظام"),
("direction","RTL","text","اتجاه الواجهة"),
("currency","SAR","text","العملة"),
("currency_name","الريال السعودي","text","اسم العملة"),
("vat_rate","15","number","نسبة ضريبة القيمة المضافة"),
("invoice_prefix","INV","text","بادئة الفواتير"),
("purchase_prefix","PUR","text","بادئة المشتريات"),
("customer_prefix","CUS","text","بادئة العملاء"),
("supplier_prefix","SUP","text","بادئة الموردين"),
("product_prefix","PRD","text","بادئة المنتجات"),
("low_stock_alert","1","boolean","تنبيه انخفاض المخزون"),
("offline_first","1","boolean","التشغيل دون اتصال"),
]

if exists("system_settings"):
    for key,val,typ,desc in settings:
        row=cur.execute(
            "SELECT id FROM system_settings WHERE setting_key=?",
            (key,)
        ).fetchone()
        data={
            "setting_key":key,
            "setting_value":val,
            "value_type":typ,
            "description":desc
        }
        if row:
            update_id("system_settings",row[0],data)
        else:
            insert_row("system_settings",data)

# ------------------------------------------------------------------
# المنطقة التخزينية
# ------------------------------------------------------------------
if exists("warehouse_zones"):
    upsert_by_id("warehouse_zones",1,{
        "warehouse_id":1,
        "name":"منطقة التخزين الرئيسية",
        "code":"ZONE-01"
    })

# ------------------------------------------------------------------
# أسعار المنتجات
# ------------------------------------------------------------------
if exists("product_prices"):
    for i,p in enumerate(products,1):
        sale=p[6]
        existing=cur.execute(
            "SELECT id FROM product_prices WHERE product_id=? AND price_type='RETAIL'",
            (i,)
        ).fetchone()
        data={
            "product_id":i,
            "price_type":"RETAIL",
            "price":sale,
            "min_quantity":1,
            "start_date":"2026-01-01",
            "end_date":None,
            "is_active":1
        }
        if existing:
            update_id("product_prices",existing[0],data)
        else:
            insert_row("product_prices",data)

# ------------------------------------------------------------------
# مواقع المنتجات والمخزون الأساسي
# ------------------------------------------------------------------
if exists("product_locations"):
    for i,p in enumerate(products,1):
        row=cur.execute(
            "SELECT id FROM product_locations WHERE product_id=? AND warehouse_id=?",
            (i,1)
        ).fetchone()
        data={
            "product_id":i,
            "warehouse_id":1,
            "bin_id":None,
            "quantity":20
        }
        if row:
            update_id("product_locations",row[0],data)
        else:
            insert_row("product_locations",data)

if exists("stock_balances"):
    for i,p in enumerate(products,1):
        row=cur.execute(
            "SELECT id FROM stock_balances WHERE product_id=? AND warehouse_id=?",
            (i,1)
        ).fetchone()
        data={
            "product_id":i,
            "warehouse_id":1,
            "quantity":20,
            "reserved_quantity":0,
            "average_cost":p[5],
            "last_movement_at":datetime.datetime.now().isoformat()
        }
        if row:
            update_id("stock_balances",row[0],data)
        else:
            insert_row("stock_balances",data)

# ------------------------------------------------------------------
# نظام البحث — مهم جدًا للـ POS
# ------------------------------------------------------------------
if exists("search_index"):
    cur.execute("DELETE FROM search_index WHERE entity_type='PRODUCT'")
    for i,p in enumerate(products,1):
        sku,name = p[0],p[1]
        barcode=f"628000000{i:03d}"
        search_text=f"{sku} {name} {barcode} {name}"
        insert_row("search_index",{
            "entity_type":"PRODUCT",
            "entity_id":i,
            "search_text":search_text,
            "updated_at":datetime.datetime.now().isoformat()
        })

# ------------------------------------------------------------------
# الإشعارات
# ------------------------------------------------------------------
if exists("notification_types"):
    nt=[
        ("LOW_STOCK","انخفاض المخزون","WARNING"),
        ("CUSTOMER_DUE","مستحقات العملاء","WARNING"),
        ("SUPPLIER_DUE","مستحقات الموردين","WARNING"),
        ("CASH_DIFFERENCE","فرق الخزينة","CRITICAL"),
        ("CONTRACT_EXPIRY","انتهاء عقد","WARNING"),
        ("SYSTEM","إشعار النظام","INFO"),
    ]
    for i,code,name,sev in nt:
        upsert_by_id("notification_types",i,{
            "code":code,
            "name":name,
            "severity":sev,
            "is_active":1
        })

# ------------------------------------------------------------------
# إعدادات النسخ الاحتياطي
# ------------------------------------------------------------------
if exists("backup_settings"):
    bs=[
        ("backup_enabled","1"),
        ("backup_directory","backups"),
        ("backup_frequency","daily"),
        ("keep_copies","30"),
    ]
    for i,(k,v) in enumerate(bs,1):
        upsert_by_id("backup_settings",i,{
            "setting_key":k,
            "setting_value":v
        })

# ------------------------------------------------------------------
# الحسابات المرتبطة بالخزينة والبنك
# ------------------------------------------------------------------
if exists("account_balances") and exists("fiscal_periods"):
    fp=cur.execute("SELECT id FROM fiscal_periods ORDER BY id LIMIT 1").fetchone()
    if fp:
        for aid in [1,2,3,4,5,6,7,8,9,10]:
            if cur.execute("SELECT 1 FROM accounts WHERE id=?",(aid,)).fetchone():
                row=cur.execute(
                    "SELECT id FROM account_balances WHERE account_id=? AND fiscal_period_id=?",
                    (aid,fp[0])
                ).fetchone()
                if not row:
                    insert_row("account_balances",{
                        "account_id":aid,
                        "fiscal_period_id":fp[0],
                        "debit":0,
                        "credit":0,
                        "balance":0
                    })

# ------------------------------------------------------------------
# بيانات الموظف الأول إن وجد
# ------------------------------------------------------------------
if exists("users"):
    update_id("users",1,{
        "username":"admin",
        "full_name":"مدير النظام",
        "phone":"",
        "email":"",
        "is_active":1,
        "is_locked":0,
        "failed_login_attempts":0
    })

# ------------------------------------------------------------------
# تحديث اسم النظام
# ------------------------------------------------------------------
if exists("system_info"):
    update_id("system_info",1,{
        "system_name":"نظام القرطاسية",
        "version":"1.0.0"
    })

# ------------------------------------------------------------------
# حفظ
# ------------------------------------------------------------------
con.commit()

# ------------------------------------------------------------------
# فحوصات نهائية
# ------------------------------------------------------------------
print("\n"+"="*80)
print("التحقق النهائي")
print("="*80)

integrity=cur.execute("PRAGMA integrity_check").fetchone()[0]
fk=cur.execute("PRAGMA foreign_key_check").fetchall()

product_count=cur.execute("SELECT COUNT(*) FROM products").fetchone()[0] if exists("products") else 0
arabic_count=cur.execute(
    "SELECT COUNT(*) FROM products WHERE name_ar GLOB '*[ء-ي]*'"
).fetchone()[0] if exists("products") else 0

print("DATABASE INTEGRITY:",integrity)
print("FOREIGN KEYS:",len(fk))
print("PRODUCTS:",product_count)
print("ARABIC PRODUCTS:",arabic_count)

print("\nأمثلة بحث المنتجات:")
for term in ["1","PEN-001","قلم","دفتر","628000000001"]:
    rows=cur.execute("""
        SELECT id,sku,name_ar
        FROM products
        WHERE sku LIKE ?
           OR name_ar LIKE ?
           OR name_en LIKE ?
        LIMIT 5
    """,(f"%{term}%",f"%{term}%",f"%{term}%")).fetchall()
    print(term, "=>", rows)

print("\nأعداد البيانات:")
for t in [
    "companies","branches","warehouses","departments","employees",
    "units","product_categories","brands","products","customers",
    "suppliers","accounts","chart_of_accounts","banks","bank_accounts",
    "cash_registers","printing_services","product_barcodes",
    "product_locations","stock_balances","system_settings"
]:
    if exists(t):
        print(f"{t:25} {cur.execute(f'SELECT COUNT(*) FROM \"{t}\"').fetchone()[0]}")

# المحاسبة
if exists("journal_entry_lines"):
    debit=cur.execute("SELECT COALESCE(SUM(debit),0) FROM journal_entry_lines").fetchone()[0]
    credit=cur.execute("SELECT COALESCE(SUM(credit),0) FROM journal_entry_lines").fetchone()[0]
    print("\nACCOUNTING DEBIT :",round(debit,2))
    print("ACCOUNTING CREDIT:",round(credit,2))
    print("ACCOUNTING BALANCE:", "BALANCED" if abs(debit-credit)<0.01 else "CHECK REQUIRED")

if integrity=="ok" and len(fk)==0 and product_count>=31 and arabic_count>=31:
    print("\nSTATUS: SUCCESS")
else:
    print("\nSTATUS: CHECK REQUIRED")

con.close()
