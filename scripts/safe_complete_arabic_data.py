import sqlite3, shutil, os, datetime

DB="database/nizam_alqirtasiyah.db"
os.makedirs("backups",exist_ok=True)
stamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup=f"backups/safe_arabic_data_{stamp}.db"
shutil.copy2(DB,backup)

c=sqlite3.connect(DB)
c.execute("PRAGMA foreign_keys=ON")
c.execute("PRAGMA journal_mode=WAL")
cur=c.cursor()

def tables():
    return {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")}

T=tables()

def C(t):
    return {r[1] for r in cur.execute(f'PRAGMA table_info("{t}")')}

def safe_update(t,where,values):
    if t not in T:return
    cc=C(t)
    values={k:v for k,v in values.items() if k in cc}
    if not values:return
    wkeys=list(where)
    sql=f'UPDATE "{t}" SET '+",".join(f'"{k}"=?' for k in values)
    sql+=' WHERE '+ " AND ".join(f'"{k}"=?' for k in wkeys)
    try:cur.execute(sql,tuple(values.values())+tuple(where.values()))
    except sqlite3.IntegrityError:pass

def safe_insert(t,values):
    if t not in T:return None
    cc=C(t)
    values={k:v for k,v in values.items() if k in cc}
    if not values:return None
    try:
        keys=list(values)
        cur.execute(
            f'INSERT INTO "{t}" ({",".join(chr(34)+x+chr(34) for x in keys)}) VALUES ({",".join("?" for x in keys)})',
            tuple(values[x] for x in keys)
        )
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return None

def put_name(t,name,extra=None):
    if t not in T:return None
    cc=C(t)
    row=None
    if "name" in cc:
        row=cur.execute(f'SELECT id FROM "{t}" WHERE name=? LIMIT 1',(name,)).fetchone()
    if row:
        safe_update(t,{"id":row[0]},dict(extra or {},name=name))
        return row[0]
    d=dict(extra or {})
    if "name" in cc:d["name"]=name
    return safe_insert(t,d)

def put_code(t,code,extra):
    if t not in T:return None
    cc=C(t)
    row=None
    for field in ("code","sku","employee_no","customer_code","supplier_code"):
        if field in cc:
            row=cur.execute(f'SELECT id FROM "{t}" WHERE "{field}"=? LIMIT 1',(code,)).fetchone()
            if row:
                safe_update(t,{"id":row[0]},extra)
                return row[0]
    d=dict(extra)
    if "code" in cc:d["code"]=code
    elif "sku" in cc:d["sku"]=code
    elif "employee_no" in cc:d["employee_no"]=code
    elif "customer_code" in cc:d["customer_code"]=code
    elif "supplier_code" in cc:d["supplier_code"]=code
    return safe_insert(t,d)

print("="*80)
print("إصلاح شامل وآمن للبيانات العربية")
print("="*80)
print("BACKUP:",backup)

# الأقسام
departments=[
"الإدارة","المبيعات","المشتريات","المخزون والمستودعات",
"المحاسبة والمالية","خدمة العملاء","الطباعة والتصوير"
]
for x in departments: put_name("departments",x,{"is_active":1})

# الوظائف
positions=[
("مدير الفرع",1,7000),("محاسب",5,5000),("أمين مستودع",4,4000),
("بائع",2,3500),("موظف خدمة عملاء",6,3500),
("موظف طباعة وتصوير",7,3500),("مساعد مبيعات",2,3000)
]
for n,d,s in positions:
    put_name("job_positions",n,{"department_id":d,"base_salary":s,"is_active":1})

# الوحدات
units=[
("قطعة","قطعة"),("علبة","علبة"),("باكيت","باكيت"),("كرتون","كرتون"),
("دفتر","دفتر"),("مجلد","مجلد"),("متر","م"),("خدمة","خدمة")
]
for n,s in units:put_name("units",n,{"symbol":s,"is_active":1})

# التصنيفات
cats=[
("أدوات الكتابة","CAT-01"),("الدفاتر والكراسات","CAT-02"),
("الرسم والتلوين","CAT-03"),("الورق","CAT-04"),
("الملفات والمجلدات","CAT-05"),("الأدوات الهندسية","CAT-06"),
("المستلزمات المدرسية","CAT-07"),("القرطاسية المكتبية","CAT-08"),
("الطباعة والتصوير","CAT-09"),("الأحبار ومستلزمات الطباعة","CAT-10"),
("المستلزمات التقنية","CAT-11"),("الهدايا","CAT-12"),
("الحقائب","CAT-13"),("مستلزمات الجامعة","CAT-14")
]
catids={}
for n,code in cats:
    if "product_categories" in T:
        row=cur.execute('SELECT id FROM product_categories WHERE code=? OR name=? LIMIT 1',(code,n)).fetchone()
        if row:
            catids[n]=row[0]
            safe_update("product_categories",{"id":row[0]},{"name":n,"code":code,"description":n,"is_active":1})
        else:
            catids[n]=safe_insert("product_categories",{"name":n,"code":code,"description":n,"is_active":1})

# الماركات
brands=["بيك","فابر كاستل","ستابلر","مابيد","بنتل","ساكورا","ماركة لؤلؤة"]
brandids={}
for n in brands:
    if "brands" in T:
        row=cur.execute("SELECT id FROM brands WHERE name=? LIMIT 1",(n,)).fetchone()
        if row:
            brandids[n]=row[0]
            safe_update("brands",{"id":row[0]},{"name":n,"description":"منتجات قرطاسية","is_active":1})
        else:brandids[n]=safe_insert("brands",{"name":n,"description":"منتجات قرطاسية","is_active":1})

# المنتجات
products=[
("PEN-001","قلم جاف أزرق","أدوات الكتابة","بيك",2,3),
("PEN-002","قلم جاف أسود","أدوات الكتابة","بيك",2,3),
("PEN-003","قلم جاف أحمر","أدوات الكتابة","بيك",2,3),
("PEN-004","قلم رصاص HB","أدوات الكتابة","فابر كاستل",1.5,2.5),
("PEN-005","قلم رصاص 2B","أدوات الكتابة","فابر كاستل",1.5,2.5),
("PEN-006","قلم تحديد أصفر","أدوات الكتابة","ستابلر",2.5,4),
("NB-001","دفتر 100 ورقة مسطر","الدفاتر والكراسات","ماركة لؤلؤة",8,12),
("NB-002","دفتر 200 ورقة مسطر","الدفاتر والكراسات","ماركة لؤلؤة",14,20),
("NB-003","كراسة 60 ورقة","الدفاتر والكراسات","ماركة لؤلؤة",4,7),
("NB-004","دفتر رسم","الرسم والتلوين","فابر كاستل",6,10),
("ART-001","علبة ألوان خشبية 12 لون","الرسم والتلوين","فابر كاستل",8,14),
("ART-002","ألوان شمعية 12 لون","الرسم والتلوين","فابر كاستل",6,10),
("ART-003","ألوان مائية","الرسم والتلوين","ساكورا",7,12),
("PAPER-001","ورق تصوير A4 أبيض 80 جرام","الورق","ماركة لؤلؤة",14,22),
("PAPER-002","ورق ملون A4","الورق","ماركة لؤلؤة",12,20),
("FILE-001","ملف بلاستيكي شفاف","الملفات والمجلدات","ماركة لؤلؤة",1.5,3),
("FILE-002","مجلد حلقي","الملفات والمجلدات","ماركة لؤلؤة",6,10),
("GEO-001","مسطرة 30 سم","الأدوات الهندسية","مابيد",1.5,3),
("GEO-002","طقم هندسي","الأدوات الهندسية","مابيد",5,9),
("SCHOOL-001","ممحاة بيضاء","المستلزمات المدرسية","فابر كاستل",1,2),
("SCHOOL-002","براية معدنية","المستلزمات المدرسية","مابيد",2,4),
("SCHOOL-003","مقص مدرسي","المستلزمات المدرسية","مابيد",3.5,6),
("OFFICE-001","دباسة مكتبية","القرطاسية المكتبية","ستابلر",8,14),
("OFFICE-002","علبة دبابيس دباسة","القرطاسية المكتبية","ستابلر",2,4),
("OFFICE-003","شريط لاصق","القرطاسية المكتبية","ماركة لؤلؤة",2,4),
("INK-001","حبر طابعة أسود","الأحبار ومستلزمات الطباعة","ماركة لؤلؤة",35,55),
("INK-002","حبر طابعة ملون","الأحبار ومستلزمات الطباعة","ماركة لؤلؤة",40,65),
("BAG-001","حقيبة مدرسية","الحقائب","ماركة لؤلؤة",45,70),
("TECH-001","ذاكرة USB سعة 32 جيجابايت","المستلزمات التقنية","ماركة لؤلؤة",18,30),
("UNIV-001","دفتر جامعي 200 ورقة","مستلزمات الجامعة","ماركة لؤلؤة",15,23),
("OFFICE-004","آلة حاسبة مكتبية","القرطاسية المكتبية","مابيد",18,30)
]

prodids={}
for sku,name,cat,brand,cost,sale in products:
    if "products" not in T:continue
    row=cur.execute("SELECT id FROM products WHERE sku=? LIMIT 1",(sku,)).fetchone()
    data={
        "sku":sku,"name_ar":name,"name_en":name,
        "category_id":catids.get(cat),
        "brand_id":brandids.get(brand),
        "unit_id":1,"product_type":"PRODUCT",
        "description":name,"cost_price":cost,"sale_price":sale,
        "wholesale_price":round(sale*.9,2),
        "school_price":round(sale*.87,2),
        "corporate_price":round(sale*.84,2),
        "min_price":sale,"reorder_point":5,
        "min_stock":5,"max_stock":100,"is_active":1,
        "updated_at":datetime.datetime.now().isoformat()
    }
    if row:
        prodids[sku]=row[0]
        safe_update("products",{"id":row[0]},data)
    else:
        prodids[sku]=safe_insert("products",data)

# الباركود والمخزون
for i,(sku,name,cat,brand,cost,sale) in enumerate(products,1):
    pid=prodids.get(sku)
    if not pid:continue
    barcode=f"628000000{i:03d}"
    if "product_barcodes" in T:
        row=cur.execute("SELECT id FROM product_barcodes WHERE product_id=? LIMIT 1",(pid,)).fetchone()
        if row:safe_update("product_barcodes",{"id":row[0]},{"barcode":barcode,"is_primary":1})
        else:safe_insert("product_barcodes",{"product_id":pid,"barcode":barcode,"is_primary":1})
    if "stock_balances" in T:
        row=cur.execute("SELECT id FROM stock_balances WHERE product_id=? AND warehouse_id=1 LIMIT 1",(pid,)).fetchone()
        d={"product_id":pid,"warehouse_id":1,"quantity":20,"reserved_quantity":0,"average_cost":cost,"last_movement_at":datetime.datetime.now().isoformat()}
        if row:safe_update("stock_balances",{"id":row[0]},d)
        else:safe_insert("stock_balances",d)
    if "product_locations" in T:
        row=cur.execute("SELECT id FROM product_locations WHERE product_id=? AND warehouse_id=1 LIMIT 1",(pid,)).fetchone()
        d={"product_id":pid,"warehouse_id":1,"quantity":20}
        if row:safe_update("product_locations",{"id":row[0]},d)
        else:safe_insert("product_locations",d)

# العملاء
customer_names=[
"عميل نقدي","مدرسة اليقظة","مدرسة الإبداع الأهلية","مدرسة النخبة",
"جامعة الملك عبدالعزيز","شركة الإمداد المكتبي","مؤسسة رواد التعليم",
"مكتبة الطالب","مدارس المستقبل","مؤسسة الصفوة"
]
for i,n in enumerate(customer_names,1):
    put_code("customers",f"CUS-{i:03d}",{
        "name":n,"customer_type":"RETAIL" if i==1 else "CORPORATE",
        "group_id":1,"phone":f"050000{1000+i:04d}",
        "credit_limit":0 if i==1 else 5000,
        "opening_balance":0,"current_balance":0,"is_active":1,
        "updated_at":datetime.datetime.now().isoformat()
    })

# الموردون
supplier_names=[
"شركة المورد الأول للقرطاسية","مؤسسة الإمداد المدرسي","شركة الورق المتحدة",
"مؤسسة أدوات التعليم","شركة الأحبار والطباعة","مؤسسة الحقائب المدرسية",
"شركة التقنية المكتبية","مؤسسة اللوازم المكتبية","شركة القرطاسية الحديثة",
"مؤسسة تجهيز المدارس"
]
for i,n in enumerate(supplier_names,1):
    put_code("suppliers",f"SUP-{i:03d}",{
        "name":n,"supplier_type":"LOCAL",
        "phone":f"055000{1000+i:04d}",
        "address":"المملكة العربية السعودية",
        "credit_limit":10000,"current_balance":0,
        "group_id":1 if i<=5 else 2,"is_active":1
    })

# الموظفون
for i,(n,d,p,s) in enumerate([
("مدير الفرع",1,1,7000),("محاسب الفرع",5,2,5000),
("أمين المستودع",4,3,4000),("موظف مبيعات",2,4,3500),
("موظف خدمة العملاء",6,5,3500),("موظف الطباعة والتصوير",7,6,3500)
],1):
    put_code("employees",f"EMP-{i:03d}",{
        "full_name":n,"phone":f"050000{2000+i:04d}",
        "department_id":d,"position_id":p,
        "hire_date":"2026-01-01","status":"ACTIVE","basic_salary":s
    })

# الحسابات
accounts=[
("1100","الخزينة","ASSET"),("1200","البنوك","ASSET"),
("1300","العملاء","ASSET"),("1400","المخزون","ASSET"),
("1410","ضريبة القيمة المضافة - مدخلات","ASSET"),
("1500","الأصول الثابتة","ASSET"),("2100","الموردون","LIABILITY"),
("2200","ضريبة القيمة المضافة - مخرجات","LIABILITY"),
("3100","رأس المال","EQUITY"),("4100","مبيعات القرطاسية","REVENUE"),
("4200","إيرادات الطباعة والتصوير","REVENUE"),
("4300","إيرادات الخدمات","REVENUE"),("5100","تكلفة البضاعة المباعة","EXPENSE"),
("5200","مصروفات الرواتب","EXPENSE"),("5300","مصروفات الكهرباء والمياه","EXPENSE"),
("5400","مصروفات الإيجار","EXPENSE"),("5500","مصروفات التشغيل","EXPENSE")
]
for code,name,typ in accounts:
    if "accounts" in T:
        row=cur.execute("SELECT id FROM accounts WHERE account_code=? LIMIT 1",(code,)).fetchone()
        d={"account_code":code,"account_name":name,"account_type":typ,"is_active":1,"allow_posting":1}
        if row:safe_update("accounts",{"id":row[0]},d)
        else:safe_insert("accounts",d)

# البنك والخزينة
if "banks" in T:
    put_code("banks","BANK-001",{"name":"البنك الرئيسي","is_active":1})
if "bank_accounts" in T:
    row=cur.execute("SELECT id FROM bank_accounts LIMIT 1").fetchone()
    d={"bank_id":1,"branch_id":1,"account_name":"الحساب البنكي الرئيسي","currency_code":"SAR","opening_balance":0,"current_balance":0,"is_active":1}
    if row:safe_update("bank_accounts",{"id":row[0]},d)
    else:safe_insert("bank_accounts",d)
if "cash_registers" in T:
    put_code("cash_registers","CASH-001",{"branch_id":1,"name":"الخزينة الرئيسية","is_active":1})

# إعدادات النظام
settings=[
("company_name","قرطاسية لؤلؤة الأربعين النموذجية","text","اسم المنشأة"),
("system_name","نظام القرطاسية","text","اسم النظام"),
("language","العربية","text","لغة النظام"),
("direction","RTL","text","اتجاه الواجهة"),
("currency","SAR","text","العملة"),
("currency_name","الريال السعودي","text","اسم العملة"),
("vat_rate","15","number","نسبة ضريبة القيمة المضافة"),
("offline_first","1","boolean","التشغيل دون اتصال")
]
for k,v,t,d in settings:
    if "system_settings" in T:
        row=cur.execute("SELECT id FROM system_settings WHERE setting_key=? LIMIT 1",(k,)).fetchone()
        data={"setting_key":k,"setting_value":v,"value_type":t,"description":d,"updated_at":datetime.datetime.now().isoformat()}
        if row:safe_update("system_settings",{"id":row[0]},data)
        else:safe_insert("system_settings",data)

# فهرس البحث
if "search_index" in T:
    cur.execute("DELETE FROM search_index WHERE entity_type='PRODUCT'")
    for i,(sku,name,*_) in enumerate(products,1):
        pid=prodids.get(sku)
        if pid:
            safe_insert("search_index",{
                "entity_type":"PRODUCT","entity_id":pid,
                "search_text":f"{sku} {name} {name} 628000000{i:03d}",
                "updated_at":datetime.datetime.now().isoformat()
            })

c.commit()

integrity=cur.execute("PRAGMA integrity_check").fetchone()[0]
fk=cur.execute("PRAGMA foreign_key_check").fetchall()
pc=cur.execute("SELECT COUNT(*) FROM products").fetchone()[0]
arabic=cur.execute("SELECT COUNT(*) FROM products WHERE name_ar GLOB '*[ء-ي]*'").fetchone()[0]

print("\n"+"="*80)
print("النتيجة النهائية")
print("="*80)
print("DATABASE INTEGRITY:",integrity)
print("FOREIGN KEYS:",len(fk))
print("PRODUCTS:",pc)
print("ARABIC PRODUCTS:",arabic)

for q in ["1","PEN-001","قلم","دفتر","628000000001"]:
    rows=cur.execute("""
    SELECT id,sku,name_ar FROM products
    WHERE sku LIKE ? OR name_ar LIKE ? OR name_en LIKE ?
    LIMIT 5
    """,(f"%{q}%",f"%{q}%",f"%{q}%")).fetchall()
    print("SEARCH",q,":",rows)

for t in ["departments","job_positions","employees","units","product_categories",
          "brands","products","customers","suppliers","accounts",
          "banks","bank_accounts","cash_registers","stock_balances",
          "product_barcodes","system_settings"]:
    if t in T:
        print(f"{t}: {cur.execute(f'SELECT COUNT(*) FROM \"{t}\"').fetchone()[0]}")

if "journal_entry_lines" in T:
    dr=cur.execute("SELECT COALESCE(SUM(debit),0) FROM journal_entry_lines").fetchone()[0]
    cr=cur.execute("SELECT COALESCE(SUM(credit),0) FROM journal_entry_lines").fetchone()[0]
    print("ACCOUNTING DEBIT :",round(dr,2))
    print("ACCOUNTING CREDIT:",round(cr,2))
    print("ACCOUNTING:", "BALANCED" if abs(dr-cr)<0.01 else "CHECK REQUIRED")

print("STATUS:", "SUCCESS" if integrity=="ok" and len(fk)==0 and pc>=31 and arabic>=31 else "CHECK REQUIRED")
c.close()
