import sqlite3, os, shutil, datetime, traceback

BASE=os.getcwd()
DB=os.path.join(BASE,"database","nizam_alqirtasiyah.db")
BACK=os.path.join(BASE,"backups")
os.makedirs(BACK,exist_ok=True)
stamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup=os.path.join(BACK,f"before_safe_operational_seed_{stamp}.db")

print("="*70)
print("SAFE OPERATIONAL DATA REPAIR / SEED")
print("="*70)

if not os.path.exists(DB):
    raise SystemExit("DATABASE NOT FOUND")

shutil.copy2(DB,backup)
print("BACKUP:",backup)

con=sqlite3.connect(DB)
con.execute("PRAGMA foreign_keys=ON")
con.execute("PRAGMA busy_timeout=10000")

def cols(table):
    return {r[1] for r in con.execute(f'PRAGMA table_info("{table}")').fetchall()}

def exists(table):
    return bool(con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone())

def first_id(table):
    if not exists(table): return None
    r=con.execute(f'SELECT id FROM "{table}" ORDER BY id LIMIT 1').fetchone()
    return r[0] if r else None

def insert_dynamic(table,data,ignore=True):
    if not exists(table): return None
    c=cols(table)
    data={k:v for k,v in data.items() if k in c}
    if not data: return None
    names=list(data)
    marks=",".join("?" for _ in names)
    verb="INSERT OR IGNORE" if ignore else "INSERT"
    sql=f'{verb} INTO "{table}" ({",".join(chr(34)+x+chr(34) for x in names)}) VALUES ({marks})'
    con.execute(sql,[data[x] for x in names])
    if "id" in c:
        # ابحث عن الصف بنفس القيم الفريدة الممكنة
        for key in ("supplier_code","customer_code","sku","code","account_code","invoice_number","order_number"):
            if key in data:
                r=con.execute(f'SELECT id FROM "{table}" WHERE "{key}"=? LIMIT 1',(data[key],)).fetchone()
                if r: return r[0]
    return con.execute("SELECT last_insert_rowid()").fetchone()[0]

def get_by(table,key,value):
    if not exists(table) or key not in cols(table): return None
    r=con.execute(f'SELECT id FROM "{table}" WHERE "{key}"=? LIMIT 1',(value,)).fetchone()
    return r[0] if r else None

try:
    now=datetime.datetime.now().isoformat(sep=" ",timespec="seconds")

    # ------------------------------------------------------------
    # 1) الموردون: لا تكرار إطلاقًا
    # ------------------------------------------------------------
    supplier_data=[
        ("SUP-0001","شركة التوريد الأولى","0500000001"),
        ("SUP-0002","مؤسسة القرطاسية الحديثة","0500000002"),
        ("SUP-0003","مورد الأدوات المدرسية","0500000003"),
    ]

    supplier_ids=[]
    sc=cols("suppliers")
    print("\nSUPPLIERS COLUMNS:",sorted(sc))

    for code,name,phone in supplier_data:
        sid=get_by("suppliers","supplier_code",code)
        if sid is None:
            data={
                "supplier_code":code,
                "name":name,
                "name_ar":name,
                "name_en":name,
                "phone":phone,
                "mobile":phone,
                "email":code.lower()+"@example.local",
                "address":"عنوان المورد",
                "city":"جدة",
                "country":"السعودية",
                "is_active":1,
                "created_at":now,
                "updated_at":now,
            }
            sid=insert_dynamic("suppliers",data,True)
        if sid: supplier_ids.append(sid)

    # ------------------------------------------------------------
    # 2) العملاء: لا تكرار
    # ------------------------------------------------------------
    customer_data=[
        ("CUS-0001","عميل نقدي","0500000101"),
        ("CUS-0002","مدرسة نموذجية","0500000102"),
        ("CUS-0003","طالب جامعي","0500000103"),
        ("CUS-0004","عميل آجل","0500000104"),
    ]

    customer_ids=[]
    cc=cols("customers")
    print("CUSTOMERS COLUMNS:",sorted(cc))

    for code,name,phone in customer_data:
        cid=get_by("customers","customer_code",code)
        if cid is None:
            data={
                "customer_code":code,
                "name":name,
                "name_ar":name,
                "name_en":name,
                "phone":phone,
                "mobile":phone,
                "email":code.lower()+"@example.local",
                "address":"عنوان العميل",
                "city":"جدة",
                "country":"السعودية",
                "is_active":1,
                "created_at":now,
                "updated_at":now,
            }
            cid=insert_dynamic("customers",data,True)
        if cid: customer_ids.append(cid)

    # ------------------------------------------------------------
    # 3) المنتج: استخدم الموجود أو أنشئه
    # ------------------------------------------------------------
    product_id=get_by("products","sku","P-0001")
    if product_id is None:
        category_id=first_id("product_categories")
        brand_id=first_id("brands")
        unit_id=first_id("units")
        data={
            "sku":"P-0001",
            "name_ar":"دفتر مدرسي",
            "name_en":"School Notebook",
            "category_id":category_id,
            "brand_id":brand_id,
            "unit_id":unit_id,
            "product_type":"PRODUCT",
            "description":"دفتر مدرسي تجريبي",
            "cost_price":10,
            "sale_price":15,
            "wholesale_price":13,
            "school_price":12,
            "corporate_price":12,
            "min_price":10,
            "reorder_point":5,
            "min_stock":2,
            "max_stock":100,
            "is_active":1,
            "created_at":now,
            "updated_at":now,
        }
        product_id=insert_dynamic("products",data,True)

    # ------------------------------------------------------------
    # 4) الحسابات الضريبية المطلوبة
    # ------------------------------------------------------------
    accounts=[
        ("1410","ضريبة القيمة المضافة - مدخلات","asset"),
        ("2200","ضريبة القيمة المضافة - مخرجات","liability"),
    ]
    if exists("accounts"):
        ac=cols("accounts")
        for code,name,typ in accounts:
            if not get_by("accounts","account_code",code):
                insert_dynamic("accounts",{
                    "account_code":code,
                    "account_name":name,
                    "account_type":typ,
                    "is_active":1,
                    "allow_posting":1,
                    "opening_balance":0,
                    "created_at":now
                },True)

    # ------------------------------------------------------------
    # 5) إصلاح أي FK orphaned في purchase_requests / sale_returns
    # ------------------------------------------------------------
    uid=first_id("users")
    bid=first_id("branches")
    wid=first_id("warehouses")

    if exists("purchase_requests") and uid:
        c=cols("purchase_requests")
        if "created_by" in c:
            con.execute("UPDATE purchase_requests SET created_by=? WHERE created_by IS NULL OR created_by NOT IN (SELECT id FROM users)",(uid,))
        if "user_id" in c:
            con.execute("UPDATE purchase_requests SET user_id=? WHERE user_id IS NULL OR user_id NOT IN (SELECT id FROM users)",(uid,))

    if exists("sale_returns") and uid:
        c=cols("sale_returns")
        if "created_by" in c:
            con.execute("UPDATE sale_returns SET created_by=? WHERE created_by IS NULL OR created_by NOT IN (SELECT id FROM users)",(uid,))
        if "user_id" in c:
            con.execute("UPDATE sale_returns SET user_id=? WHERE user_id IS NULL OR user_id NOT IN (SELECT id FROM users)",(uid,))

    # ------------------------------------------------------------
    # 6) فحص المخزون والحسابات والبيانات الرئيسية
    # ------------------------------------------------------------
    print("\nMASTER DATA")
    for t in ["companies","branches","warehouses","product_categories","brands","units",
              "products","customers","suppliers","accounts","tax_rates","users"]:
        if exists(t):
            n=con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
            print(f"{t:25} {n}")

    # ------------------------------------------------------------
    # 7) فحص شامل قبل الحفظ
    # ------------------------------------------------------------
    con.execute("PRAGMA foreign_key_check")
    fk=con.execute("PRAGMA foreign_key_check").fetchall()

    if fk:
        print("\nFOREIGN KEY ERRORS:")
        for x in fk[:20]: print(x)
        raise RuntimeError(f"FOREIGN KEY ERRORS: {len(fk)}")

    con.execute("PRAGMA integrity_check")
    integrity=con.execute("PRAGMA integrity_check").fetchone()[0]

    if integrity!="ok":
        raise RuntimeError("DATABASE INTEGRITY FAILED: "+str(integrity))

    con.commit()

    print("\nOPERATIONAL TABLE COUNTS")
    for t in ["purchase_requests","purchase_orders","purchase_order_items",
              "purchase_invoices","purchase_invoice_items","stock_movements",
              "sales","sale_items","sale_payments","journal_entries",
              "journal_entry_lines","cash_transactions","tax_invoices"]:
        if exists(t):
            print(f"{t:25} {con.execute(f'SELECT COUNT(*) FROM \"{t}\"').fetchone()[0]}")

    print("\nINTEGRITY:",integrity)
    print("FOREIGN KEY ERRORS:",len(fk))
    print("STATUS: SUCCESS")
    print("="*70)

except Exception as e:
    con.rollback()
    print("\n"+"="*70)
    print("STATUS: FAILED")
    print(type(e).__name__+":"+str(e))
    print("DATABASE WAS NOT MODIFIED BY THIS RUN")
    print("BACKUP AVAILABLE:",backup)
    print("="*70)
    traceback.print_exc()
finally:
    con.close()
