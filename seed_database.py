import sqlite3, os, shutil, json, datetime, random

DB = os.path.join("database", "nizam_alqirtasiyah.db")
BACKUP_DIR = os.path.join("database", "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = os.path.join(BACKUP_DIR, f"nizam_alqirtasiyah_before_full_seed_{stamp}.db")
shutil.copy2(DB, backup)

con = sqlite3.connect(DB)
con.execute("PRAGMA foreign_keys=ON")
cur = con.cursor()

def tables():
    return [r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )]

def cols(t):
    return [r[1] for r in cur.execute(f'PRAGMA table_info("{t}")')]

def count(t):
    return cur.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]

def insert_safe(t, data):
    if t not in tables():
        return False
    cs = cols(t)
    data = {k:v for k,v in data.items() if k in cs}
    if not data:
        return False

    # تكملة الحقول الإلزامية التي قد تختلف بين نسخ المخطط.
    info = cur.execute(f'PRAGMA table_info("{t}")').fetchall()
    for r in info:
        name, notnull, default, pk = r[1], r[3], r[4], r[5]
        if notnull and default is None and not pk and name not in data:
            low = name.lower()
            typ = (r[2] or "").lower()
            if "password" in low and "hash" in low:
                data[name] = "$2b$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy"
            elif low.endswith("_id"):
                data[name] = 1
            elif "date" in low or low.endswith("_at"):
                data[name] = datetime.datetime.now().isoformat(timespec="seconds")
            elif "status" in low:
                data[name] = "ACTIVE"
            elif "code" in low or "number" in low:
                data[name] = "AUTO"
            elif "name" in low or "description" in low or "address" in low:
                data[name] = "بيانات افتراضية"
            elif any(x in typ for x in ("int","real","numeric","decimal","float")):
                data[name] = 0
            else:
                data[name] = ""

    names = list(data.keys())
    vals = [data[x] for x in names]
    marks = ",".join("?" for _ in names)
    try:
        cur.execute(
            f'INSERT OR IGNORE INTO "{t}" ({",".join(chr(34)+x+chr(34) for x in names)}) VALUES ({marks})',
            vals
        )
        return cur.rowcount > 0
    except Exception:
        return False

def find_col(t, candidates):
    cs = cols(t)
    low = {x.lower():x for x in cs}
    for c in candidates:
        if c.lower() in low:
            return low[c.lower()]
    return None

def seed_by_columns(t, records):
    if t not in tables():
        return 0
    cs = cols(t)
    added = 0
    for rec in records:
        data = {}
        for k,v in rec.items():
            if k in cs:
                data[k] = v
        if data:
            if insert_safe(t,data):
                added += 1
    return added

try:
    con.execute("BEGIN")

    now = datetime.datetime.now().isoformat(timespec="seconds")

    # =========================================================
    # بيانات الشركة / الفروع / المستودعات
    # =========================================================
    seed_by_columns("companies", [
        {"name":"قرطاسية لؤلؤة الأربعين النموذجية","tax_number":"0000000000","phone":"777000000","address":"حي الصفا، شارع عبدالله بن سهل، جدة 23456","created_at":now},
    ])

    company_id = cur.execute(
        "SELECT id FROM companies ORDER BY id LIMIT 1"
    ).fetchone()
    company_id = company_id[0] if company_id else None

    seed_by_columns("branches", [
        {"name":"الفرع الرئيسي","branch_code":"MAIN","code":"MAIN","company_id":company_id,"phone":"777000000","address":"حي الصفا، شارع عبدالله بن سهل، جدة 23456","is_active":1,"created_at":now},
    ])

    branch = cur.execute("SELECT id FROM branches ORDER BY id LIMIT 1").fetchone()
    branch_id = branch[0] if branch else None

    seed_by_columns("warehouses", [
        {"name":"المستودع الرئيسي","warehouse_code":"WH-001","code":"WH-001","branch_id":branch_id,"company_id":company_id,"is_active":1,"created_at":now},
        {"name":"مستودع الفرع","warehouse_code":"WH-002","code":"WH-002","branch_id":branch_id,"company_id":company_id,"is_active":1,"created_at":now},
    ])

    warehouse = cur.execute("SELECT id FROM warehouses ORDER BY id LIMIT 1").fetchone()
    warehouse_id = warehouse[0] if warehouse else None

    # =========================================================
    # الوحدات
    # =========================================================
    units = [
        ("قطعة","PCS"),("علبة","BOX"),("كرتون","CTN"),("دفتر","NOTEBOOK"),
        ("قلم","PEN"),("متر","M"),("كيلو","KG"),("ورقة","SHEET"),
        ("رزمة","REAM"),("خدمة","SERVICE"),("ساعة","HOUR"),("نسخة","COPY")
    ]
    for name,code in units:
        seed_by_columns("units",[{
            "name":name,"unit_name":name,"code":code,"unit_code":code,
            "is_active":1,"created_at":now
        }])

    # =========================================================
    # مجموعات الأصناف
    # =========================================================
    categories = [
        ("أقلام","PENS"),("دفاتر","NOTEBOOKS"),("أوراق","PAPER"),
        ("أدوات مدرسية","SCHOOL"),("أدوات مكتبية","OFFICE"),
        ("ألوان ورسم","ART"),("ملفات وحافظات","FILES"),
        ("مستلزمات الطباعة","PRINT"),("إكسسوارات تقنية","TECH"),
        ("هدايا","GIFTS")
    ]

    for name,code in categories:
        seed_by_columns("product_categories",[{
            "name":name,"category_name":name,"code":code,
            "category_code":code,"is_active":1,"created_at":now
        }])

    # =========================================================
    # الموردون
    # =========================================================
    suppliers = [
        ("SUP-001","مؤسسة الإمداد المكتبي","777100001"),
        ("SUP-002","شركة القرطاسية الحديثة","777100002"),
        ("SUP-003","مؤسسة النور للتوريدات","777100003"),
        ("SUP-004","شركة الأدوات المدرسية","777100004"),
        ("SUP-005","مؤسسة الإبداع للورق","777100005"),
        ("SUP-006","شركة التقنية المكتبية","777100006"),
        ("SUP-007","مؤسسة الجيل الجديد","777100007"),
        ("SUP-008","شركة الألوان والرسم","777100008"),
        ("SUP-009","مؤسسة النجاح التجارية","777100009"),
        ("SUP-010","شركة التوريد العام","777100010")
    ]

    for code,name,phone in suppliers:
        seed_by_columns("suppliers",[{
            "supplier_code":code,"code":code,"name":name,
            "supplier_type":"local","phone":phone,
            "address":"جدة","credit_limit":500000,
            "current_balance":0,"is_active":1,"created_at":now
        }])

    # =========================================================
    # العملاء
    # =========================================================
    customers = [
        ("CUS-001","محمد أحمد","777200001"),
        ("CUS-002","علي عبدالله","777200002"),
        ("CUS-003","أحمد محمد","777200003"),
        ("CUS-004","خالد علي","777200004"),
        ("CUS-005","عبدالله صالح","777200005"),
        ("CUS-006","يوسف محمد","777200006"),
        ("CUS-007","عمر أحمد","777200007"),
        ("CUS-008","سامي عبدالله","777200008"),
        ("CUS-009","محمود علي","777200009"),
        ("CUS-010","إبراهيم صالح","777200010"),
        ("CUS-011","عبدالرحمن أحمد","777200011"),
        ("CUS-012","حسن محمد","777200012"),
        ("CUS-013","سعيد عبدالله","777200013"),
        ("CUS-014","وليد علي","777200014"),
        ("CUS-015","مازن أحمد","777200015"),
        ("CUS-016","رامي صالح","777200016"),
        ("CUS-017","مؤسسة الطالب","777200017"),
        ("CUS-018","مدرسة النجاح","777200018"),
        ("CUS-019","مدرسة المستقبل","777200019"),
        ("CUS-020","مركز التعليم الحديث","777200020")
    ]

    for code,name,phone in customers:
        seed_by_columns("customers",[{
            "customer_code":code,"code":code,"name":name,
            "customer_type":"individual","phone":phone,
            "address":"جدة","credit_limit":100000,
            "current_balance":0,"is_active":1,"created_at":now
        }])

    # =========================================================
    # الموظفون
    # =========================================================
    employees = [
        ("EMP-001","مدير النظام","777300001"),
        ("EMP-002","موظف مبيعات 1","777300002"),
        ("EMP-003","موظف مبيعات 2","777300003"),
        ("EMP-004","أمين المستودع","777300004"),
        ("EMP-005","المحاسب","777300005"),
        ("EMP-006","موظف المشتريات","777300006"),
        ("EMP-007","موظف خدمة العملاء","777300007")
    ]

    for code,name,phone in employees:
        seed_by_columns("employees",[{
            "employee_code":code,"code":code,"name":name,
            "full_name":name,"phone":phone,
            "branch_id":branch_id,"is_active":1,"created_at":now
        }])

    # =========================================================
    # مستخدمو النظام (حساب إداري افتراضي للتشغيل والاختبارات)
    # =========================================================
    if "users" in tables():
        employee_id = cur.execute(
            "SELECT id FROM employees ORDER BY id LIMIT 1"
        ).fetchone()
        employee_id = employee_id[0] if employee_id else None
        user_records = [
            {
                "username":"admin",
                "login_name":"admin",
                "password_hash":"$2b$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy",
                "name":"مدير النظام",
                "full_name":"مدير النظام",
                "display_name":"مدير النظام",
                "employee_id":employee_id,
                "branch_id":branch_id,
                "is_active":1,
                "status":"ACTIVE",
                "created_at":now,
                "updated_at":now
            },
            {
                "username":"cashier",
                "login_name":"cashier",
                "password_hash":"$2b$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy",
                "name":"كاشير",
                "full_name":"كاشير",
                "display_name":"كاشير",
                "employee_id":None,
                "branch_id":branch_id,
                "is_active":1,
                "status":"ACTIVE",
                "created_at":now,
                "updated_at":now
            }
        ]
        for rec in user_records:
            seed_by_columns("users", [rec])

    # =========================================================
    # المنتجات
    # =========================================================
    products = [
        ("PRD-001","قلم جاف أزرق","أقلام",100,150),
        ("PRD-002","قلم جاف أسود","أقلام",100,150),
        ("PRD-003","قلم جاف أحمر","أقلام",100,150),
        ("PRD-004","قلم رصاص HB","أقلام",80,120),
        ("PRD-005","قلم رصاص 2B","أقلام",100,150),
        ("PRD-006","قلم حبر فاخر","أقلام",500,750),
        ("PRD-007","دفتر 40 ورقة","دفاتر",400,600),
        ("PRD-008","دفتر 60 ورقة","دفاتر",500,750),
        ("PRD-009","دفتر 80 ورقة","دفاتر",600,900),
        ("PRD-010","دفتر 100 ورقة","دفاتر",800,1200),
        ("PRD-011","دفتر جامعي","دفاتر",1000,1500),
        ("PRD-012","ورق A4 80 جرام","أوراق",3500,4500),
        ("PRD-013","رزمة ورق A4","أوراق",2500,3500),
        ("PRD-014","ملف بلاستيك","ملفات وحافظات",100,200),
        ("PRD-015","ملف كبس","ملفات وحافظات",250,400),
        ("PRD-016","دباسة صغيرة","أدوات مكتبية",700,1000),
        ("PRD-017","دبابيس دباسة","أدوات مكتبية",150,250),
        ("PRD-018","مقص متوسط","أدوات مكتبية",500,800),
        ("PRD-019","مسطرة 30 سم","أدوات مدرسية",200,350),
        ("PRD-020","ممحاة","أدوات مدرسية",100,200),
        ("PRD-021","براية","أدوات مدرسية",100,200),
        ("PRD-022","غراء سائل","أدوات مدرسية",250,400),
        ("PRD-023","ألوان خشبية 12 لون","ألوان ورسم",1200,1800),
        ("PRD-024","ألوان شمعية","ألوان ورسم",700,1000),
        ("PRD-025","ألوان مائية","ألوان ورسم",900,1400),
        ("PRD-026","فرش رسم","ألوان ورسم",500,800),
        ("PRD-027","قلم تحديد أصفر","أقلام",250,400),
        ("PRD-028","قلم تحديد أخضر","أقلام",250,400),
        ("PRD-029","قلم تحديد وردي","أقلام",250,400),
        ("PRD-030","مجلد أوراق","ملفات وحافظات",500,750),
        ("PRD-031","حافظة مستندات","ملفات وحافظات",700,1000),
        ("PRD-032","USB 32GB","إكسسوارات تقنية",2500,3500),
        ("PRD-033","USB 64GB","إكسسوارات تقنية",4000,5500),
        ("PRD-034","ماوس USB","إكسسوارات تقنية",2500,3500),
        ("PRD-035","لوحة مفاتيح USB","إكسسوارات تقنية",3500,5000),
        ("PRD-036","سماعة كمبيوتر","إكسسوارات تقنية",3000,4500),
        ("PRD-037","حبر طابعة أسود","مستلزمات الطباعة",5000,7000),
        ("PRD-038","حبر طابعة ملون","مستلزمات الطباعة",6000,8500),
        ("PRD-039","ورق صور","مستلزمات الطباعة",3000,4500),
        ("PRD-040","خدمة تصوير ورق","مستلزمات الطباعة",30,50)
    ]

    for code,name,cat,cost,sale in products:
        seed_by_columns("products",[{
            "product_code":code,"sku":code,"code":code,
            "name_ar":name,"name":name,"product_name":name,
            "category_name":cat,"unit":"قطعة",
            "cost_price":cost,"purchase_price":cost,
            "sale_price":sale,"selling_price":sale,
            "min_stock":5,"max_stock":100,
            "current_stock":50,"quantity":50,
            "is_active":1,"created_at":now
        }])

    # =========================================================
    # الحسابات المحاسبية الأساسية
    # =========================================================
    account_seed = [
        ("1100","الصندوق","ASSET"),("1200","البنوك","ASSET"),("1300","العملاء","ASSET"),
        ("1400","المخزون","ASSET"),("1500","ضريبة مدخلات","ASSET"),("2100","الموردون","LIABILITY"),
        ("2200","ضريبة مخرجات","LIABILITY"),("4100","مبيعات القرطاسية","REVENUE"),
        ("5100","تكلفة البضاعة المباعة","EXPENSE"),
    ]
    for code,name,kind in account_seed:
        seed_by_columns("accounts",[{
            "account_code":code,"account_name":name,"account_type":kind,
            "is_active":1,"allow_posting":1,"opening_balance":0,"created_at":now
        }])

    # =========================================================
    # مخزون أساسي للمنتجات الموجودة
    # =========================================================
    if "stock_balances" in tables() and warehouse_id:
        for p in cur.execute("SELECT id,cost_price FROM products ORDER BY id LIMIT 100").fetchall():
            seed_by_columns("stock_balances",[{
                "product_id":p[0],"warehouse_id":warehouse_id,"quantity":50,
                "reserved_quantity":0,"average_cost":p[1] or 0,"last_movement_at":now
            }])

    if "product_barcodes" in tables():
        for p in cur.execute("SELECT id,sku FROM products ORDER BY id LIMIT 100").fetchall():
            seed_by_columns("product_barcodes",[{
                "product_id":p[0],"barcode":"628000"+f"{p[0]:06d}","is_primary":1
            }])

    if "stock" in tables():
        pc = cols("stock")
        ptab = "products"
        for p in cur.execute("SELECT id FROM products LIMIT 100").fetchall():
            pid = p[0]
            data = {}
            if "product_id" in pc: data["product_id"]=pid
            if "warehouse_id" in pc and warehouse_id: data["warehouse_id"]=warehouse_id
            if "quantity" in pc: data["quantity"]=50
            if "current_quantity" in pc: data["current_quantity"]=50
            if "available_quantity" in pc: data["available_quantity"]=50
            if "min_stock" in pc: data["min_stock"]=5
            if "max_stock" in pc: data["max_stock"]=100
            if data: insert_safe("stock",data)

    # رفع بيانات الاختبار إلى حجم عملي مفيد دون تكرار السجلات الموجودة.
    for i in range(21, 29):
        seed_by_columns("customers",[{
            "customer_code":f"CUS-{i:03d}","name":f"عميل تجريبي {i}",
            "customer_type":"individual","phone":f"7772{i:05d}",
            "address":"جدة","credit_limit":100000,"current_balance":0,"is_active":1,"created_at":now
        }])
    for i in range(11, 19):
        seed_by_columns("suppliers",[{
            "supplier_code":f"SUP-{i:03d}","name":f"مورد تجريبي {i}",
            "supplier_type":"local","phone":f"7771{i:05d}",
            "address":"جدة","credit_limit":500000,"current_balance":0,"is_active":1,"created_at":now
        }])

    # =========================================================
    # معاملات تشغيلية تجريبية مترابطة للمراجعة والاختبار
    # =========================================================
    if branch_id and warehouse_id:
        product_rows = cur.execute("SELECT id,cost_price,sale_price FROM products ORDER BY id LIMIT 8").fetchall()
        customer_rows = cur.execute("SELECT id FROM customers ORDER BY id LIMIT 4").fetchall()
        supplier_rows = cur.execute("SELECT id FROM suppliers ORDER BY id LIMIT 6").fetchall()
        if product_rows and customer_rows and supplier_rows:
            for n in range(1,5):
                exists = cur.execute("SELECT id FROM sales WHERE invoice_number=?", (f"DEMO-SAL-{n:04d}",)).fetchone()
                if not exists:
                    pid,cost,sale = product_rows[(n-1)%len(product_rows)]
                    subtotal=float(sale or 0)*2
                    tax=round(subtotal*0.15,2)
                    total=round(subtotal+tax,2)
                    cur.execute("""INSERT INTO sales
                        (invoice_number,branch_id,warehouse_id,customer_id,cashier_id,status,subtotal,discount_amount,tax_amount,total_amount,paid_amount,due_amount,notes,created_at)
                        VALUES(?,?,?,?,NULL,'POSTED',?,0,?,?,?,0,?,?)""",
                        (f"DEMO-SAL-{n:04d}",branch_id,warehouse_id,customer_rows[n-1][0],subtotal,tax,total,total,
                         "بيانات تشغيل تجريبية",now))
                    sid=cur.lastrowid
                    cur.execute("""INSERT INTO sale_items
                        (sale_id,product_id,quantity,unit_price,discount_amount,tax_amount,line_total)
                        VALUES(?,?,?,?,0,?,?)""",
                        (sid,pid,2,float(sale or 0),tax,total))
                    cur.execute("""INSERT INTO sale_payments
                        (sale_id,payment_method,amount,reference_number,notes)
                        VALUES(?,?,?,?,?)""",(sid,"cash",total,f"DEMO-PAY-{n:04d}","دفع تجريبي"))
            for n in range(1,7):
                exists = cur.execute("SELECT id FROM purchase_invoices WHERE invoice_number=?", (f"DEMO-PUR-{n:04d}",)).fetchone()
                if not exists:
                    pid,cost,sale = product_rows[(n-1)%len(product_rows)]
                    subtotal=float(cost or 0)*5
                    tax=round(subtotal*0.15,2)
                    total=round(subtotal+tax,2)
                    cur.execute("""INSERT INTO purchase_invoices
                        (invoice_number,supplier_id,subtotal,tax_amount,total_amount,paid_amount,due_amount,status,invoice_date)
                        VALUES(?,?,?,?,?,?,?,'POSTED',CURRENT_DATE)""",
                        (f"DEMO-PUR-{n:04d}",supplier_rows[n-1][0],subtotal,tax,total,total,0))
                    iid=cur.lastrowid
                    cur.execute("""INSERT INTO purchase_invoice_items
                        (invoice_id,product_id,quantity,unit_cost,tax_amount,line_total)
                        VALUES(?,?,?,?,?,?)""",
                        (iid,pid,5,float(cost or 0),tax,total))

    # =========================================================
    # الضرائب
    # =========================================================
    tax_records = [
        {"name":"ضريبة القيمة المضافة","tax_name":"ضريبة القيمة المضافة",
         "code":"VAT","rate":15,"percentage":15,"is_active":1,"created_at":now},
        {"name":"ضريبة صفرية","tax_name":"ضريبة صفرية",
         "code":"ZERO","rate":0,"percentage":0,"is_active":1,"created_at":now},
        {"name":"معفى","tax_name":"معفى","code":"EXEMPT",
         "rate":0,"percentage":0,"is_active":1,"created_at":now}
    ]
    seed_by_columns("tax_rates",tax_records)

    # =========================================================
    # إعدادات النظام
    # =========================================================
    settings = [
        ("system_name","نظام القرطاسية"),
        ("language","ar"),
        ("direction","rtl"),
        ("currency","ريال سعودي"),
        ("currency_code","SAR"),
        ("country","المملكة العربية السعودية"),
        ("timezone","Asia/Aden"),
        ("inventory_enabled","1"),
        ("accounting_enabled","1"),
        ("pos_enabled","1"),
        ("offline_first","1"),
        ("automatic_backup","1"),
        ("audit_log_enabled","1"),
        ("tax_enabled","1"),
        ("multi_branch","1"),
        ("multi_warehouse","1")
    ]

    for k,v in settings:
        seed_by_columns("system_settings",[{
            "key":k,"name":k,"setting_key":k,
            "value":v,"setting_value":v,
            "created_at":now,"updated_at":now
        }])

    # =========================================================
    # أدوار المستخدمين
    # =========================================================
    roles = [
        ("مدير النظام","ADMIN"),
        ("مدير المبيعات","SALES_MANAGER"),
        ("كاشير","CASHIER"),
        ("محاسب","ACCOUNTANT"),
        ("أمين مستودع","WAREHOUSE"),
        ("مشتريات","PURCHASING"),
        ("خدمة العملاء","CUSTOMER_SERVICE")
    ]

    for name,code in roles:
        seed_by_columns("roles",[{
            "name":name,"role_name":name,"code":code,
            "is_active":1,"created_at":now
        }])

    # =========================================================
    # سير العمل
    # =========================================================
    workflows = [
        ("دورة المبيعات","SALES"),
        ("دورة المشتريات","PURCHASE"),
        ("دورة المرتجعات","RETURNS"),
        ("دورة المخزون","INVENTORY")
    ]

    for name,code in workflows:
        seed_by_columns("workflows",[{
            "name":name,"workflow_name":name,
            "code":code,"is_active":1,"created_at":now
        }])

    # =========================================================
    # معلومات النظام
    # =========================================================
    seed_by_columns("system_info",[{
        "key":"database_version","name":"database_version",
        "value":"1.0.0","created_at":now,"updated_at":now
    }])

    # =========================================================
    # تحديث السجلات دون حذف أي سجل موجود
    # =========================================================
    con.commit()

    # =========================================================
    # التقرير النهائي
    # =========================================================
    all_tables = tables()
    nonempty = [(t,count(t)) for t in all_tables if count(t)>0]
    empty = [t for t in all_tables if count(t)==0]

    print()
    print("="*70)
    print("تمت عملية تعبئة قاعدة البيانات بنجاح")
    print("="*70)
    print(f"النسخة الاحتياطية: {backup}")
    print(f"عدد الجداول الكلي : {len(all_tables)}")
    print(f"الجداول التي تحتوي بيانات : {len(nonempty)}")
    print(f"الجداول الفارغة : {len(empty)}")
    print()
    print("أهم البيانات الحالية:")
    for t in ["companies","branches","warehouses","products","customers","suppliers","employees","units","tax_rates","roles","workflows","system_settings"]:
        if t in all_tables:
            print(f"  {t:25} {count(t)} سجل")

    print()
    print("الجداول الفارغة المتبقية (غالبًا جداول أحداث/سجلات تاريخية):")
    print(", ".join(empty))
    print()
    print("سلامة SQLite:")
    print(cur.execute("PRAGMA integrity_check").fetchone()[0])

except Exception as e:
    con.rollback()
    print()
    print("حدث خطأ، وتم إلغاء العملية بالكامل.")
    print("الخطأ:",repr(e))
    print("القاعدة الأصلية لم تُترك في حالة جزئية.")
    raise

finally:
    con.close()
