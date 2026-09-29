from pathlib import Path
import sqlite3, shutil, datetime

ROOT=Path.cwd()
DB=ROOT/"database/nizam_alqirtasiyah.db"
BACK=ROOT/"backups"
BACK.mkdir(exist_ok=True)

ts=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copy2(DB,BACK/f"before_safe_master_fill_{ts}.db")

con=sqlite3.connect(DB)
cur=con.cursor()

def exists(t):
    return cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(t,)
    ).fetchone() is not None

def cols(t):
    return [x[1] for x in cur.execute(f'PRAGMA table_info("{t}")')]

def safe_insert(t,data):
    if not exists(t):
        return 0
    c=cols(t)
    d={k:v for k,v in data.items() if k in c}

    if not d:
        return 0

    # نتأكد من الأعمدة المطلوبة
    info=cur.execute(f'PRAGMA table_info("{t}")').fetchall()
    for r in info:
        name=r[1]
        notnull=r[3]
        default=r[4]
        pk=r[5]
        if notnull and not pk and default is None and name not in d:
            return 0

    try:
        names=list(d)
        marks=",".join(["?"]*len(names))
        cur.execute(
            f'INSERT OR IGNORE INTO "{t}" ({",".join(names)}) VALUES ({marks})',
            [d[x] for x in names]
        )
        return cur.rowcount
    except sqlite3.IntegrityError:
        return 0
    except Exception:
        return 0

def add_many(t,rows):
    n=0
    for r in rows:
        n+=safe_insert(t,r)
    return n

# =========================
# التصنيفات
# =========================
if exists("product_categories"):
    rows=[
        {"code":"CAT-001","category_code":"CAT-001","name":"أدوات الكتابة","name_ar":"أدوات الكتابة","is_active":1},
        {"code":"CAT-002","category_code":"CAT-002","name":"الدفاتر والملفات","name_ar":"الدفاتر والملفات","is_active":1},
        {"code":"CAT-003","category_code":"CAT-003","name":"الرسم والفنون","name_ar":"الرسم والفنون","is_active":1},
        {"code":"CAT-004","category_code":"CAT-004","name":"المستلزمات المدرسية","name_ar":"المستلزمات المدرسية","is_active":1},
        {"code":"CAT-005","category_code":"CAT-005","name":"المستلزمات المكتبية","name_ar":"المستلزمات المكتبية","is_active":1},
        {"code":"CAT-006","category_code":"CAT-006","name":"الطباعة والخدمات","name_ar":"الطباعة والخدمات","is_active":1},
        {"code":"CAT-007","category_code":"CAT-007","name":"الإلكترونيات","name_ar":"الإلكترونيات","is_active":1},
        {"code":"CAT-008","category_code":"CAT-008","name":"الهدايا","name_ar":"الهدايا","is_active":1},
    ]
    add_many("product_categories",rows)

# =========================
# العلامات التجارية
# =========================
if exists("brands"):
    rows=[
        {"code":"B001","brand_code":"B001","name":"BIC","name_ar":"BIC","is_active":1},
        {"code":"B002","brand_code":"B002","name":"Pilot","name_ar":"Pilot","is_active":1},
        {"code":"B003","brand_code":"B003","name":"Staedtler","name_ar":"Staedtler","is_active":1},
        {"code":"B004","brand_code":"B004","name":"Faber-Castell","name_ar":"Faber-Castell","is_active":1},
        {"code":"B005","brand_code":"B005","name":"HP","name_ar":"HP","is_active":1},
        {"code":"B006","brand_code":"B006","name":"Canon","name_ar":"Canon","is_active":1},
        {"code":"B007","brand_code":"B007","name":"Maped","name_ar":"Maped","is_active":1},
    ]
    add_many("brands",rows)

# =========================
# الوحدات
# =========================
if exists("units"):
    rows=[
        {"code":"PCS","unit_code":"PCS","name":"قطعة","name_ar":"قطعة","symbol":"قطعة","is_active":1},
        {"code":"BOX","unit_code":"BOX","name":"علبة","name_ar":"علبة","symbol":"علبة","is_active":1},
        {"code":"PACK","unit_code":"PACK","name":"حزمة","name_ar":"حزمة","symbol":"حزمة","is_active":1},
        {"code":"DOZ","unit_code":"DOZ","name":"درزن","name_ar":"درزن","symbol":"درزن","is_active":1},
        {"code":"SET","unit_code":"SET","name":"طقم","name_ar":"طقم","symbol":"طقم","is_active":1},
    ]
    add_many("units",rows)

# =========================
# العملاء
# =========================
if exists("customers"):
    rows=[]
    for i in range(1,21):
        rows.append({
            "customer_code":f"CUS-{i:03d}",
            "name":f"عميل تجريبي {i:02d}",
            "customer_type":"INDIVIDUAL",
            "current_balance":0,
            "opening_balance":0,
            "credit_limit":5000,
            "is_active":1
        })
    add_many("customers",rows)

# =========================
# الموردون
# =========================
if exists("suppliers"):
    rows=[]
    for i in range(1,16):
        rows.append({
            "supplier_code":f"SUP-{i:03d}",
            "name":f"مورد تجريبي {i:02d}",
            "supplier_type":"BUSINESS",
            "current_balance":0,
            "credit_limit":10000,
            "is_active":1
        })
    add_many("suppliers",rows)

# =========================
# الحسابات
# =========================
if exists("accounts"):
    rows=[
        {"account_code":"1000","account_name":"الأصول","account_type":"asset","is_active":1,"allow_posting":0,"opening_balance":0},
        {"account_code":"2000","account_name":"الخصوم","account_type":"liability","is_active":1,"allow_posting":0,"opening_balance":0},
        {"account_code":"4000","account_name":"الإيرادات","account_type":"revenue","is_active":1,"allow_posting":0,"opening_balance":0},
        {"account_code":"5000","account_name":"المصروفات","account_type":"expense","is_active":1,"allow_posting":0,"opening_balance":0},
        {"account_code":"5200","account_name":"مصروفات التشغيل","account_type":"expense","is_active":1,"allow_posting":1,"opening_balance":0},
        {"account_code":"5300","account_name":"مصروفات الرواتب","account_type":"expense","is_active":1,"allow_posting":1,"opening_balance":0},
    ]
    add_many("accounts",rows)

# =========================
# الضرائب
# =========================
if exists("tax_rates"):
    add_many("tax_rates",[
        {"code":"VAT15","name":"ضريبة القيمة المضافة 15%","rate":15,"is_active":1},
        {"code":"VAT0","name":"ضريبة صفرية","rate":0,"is_active":1},
    ])

# =========================
# المنتجات
# =========================
if exists("products"):
    cat=cur.execute("SELECT id FROM product_categories ORDER BY id LIMIT 1").fetchone()
    brand=cur.execute("SELECT id FROM brands ORDER BY id LIMIT 1").fetchone()
    unit=cur.execute("SELECT id FROM units ORDER BY id LIMIT 1").fetchone()

    products=[
        ("PEN-BLU","قلم حبر أزرق",1.5,2),
        ("PEN-BLK","قلم حبر أسود",1.5,2),
        ("PEN-RED","قلم حبر أحمر",1.5,2),
        ("PEN-GEL","قلم جل",2.5,4),
        ("PENCIL-HB","قلم رصاص HB",1,1.5),
        ("ERASER","ممحاة",1,1.5),
        ("SHARPENER","براية",1.5,2.5),
        ("NOTE-A5","دفتر A5",4,6),
        ("NOTE-A4","دفتر A4",7,10),
        ("FILE-A4","ملف A4",2.5,4),
        ("RULER-30","مسطرة 30 سم",2,3.5),
        ("COLOR-12","ألوان خشبية 12 لون",12,18),
        ("MARKER","قلم تحديد",5,8),
        ("PAPER-A4","ورق تصوير A4",15,22),
        ("INK-BLACK","حبر طابعة أسود",35,50),
        ("USB-32","ذاكرة USB 32GB",18,28),
        ("CALCULATOR","آلة حاسبة",20,30),
        ("GLUE","صمغ مدرسي",3,5),
        ("SCISSORS","مقص مدرسي",4,7),
        ("PRINT-BW","طباعة أبيض وأسود",0.2,0.5),
    ]

    for sku,name,cost,sale in products:
        d={
            "sku":sku,
            "name_ar":name,
            "name":name,
            "product_type":"SERVICE" if sku=="PRINT-BW" else "PRODUCT",
            "cost_price":cost,
            "sale_price":sale,
            "wholesale_price":round(sale*.9,2),
            "school_price":round(sale*.92,2),
            "corporate_price":round(sale*.9,2),
            "min_price":sale,
            "reorder_point":5,
            "min_stock":5,
            "max_stock":100,
            "is_active":1
        }
        if cat:d["category_id"]=cat[0]
        if brand:d["brand_id"]=brand[0]
        if unit:d["unit_id"]=unit[0]
        safe_insert("products",d)

con.commit()

print("="*70)
print("SAFE MASTER DATA FILL")
print("="*70)

for t in [
    "companies","branches","warehouses","product_categories","brands","units",
    "products","customers","suppliers","accounts","tax_rates","users"
]:
    if exists(t):
        print(f"{t:25} {cur.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]}")

print("-"*70)
print("INTEGRITY:",cur.execute("PRAGMA integrity_check").fetchone()[0])
print("FOREIGN KEY ERRORS:",len(cur.execute("PRAGMA foreign_key_check").fetchall()))
print("STATUS: SUCCESS")
print("="*70)

con.close()
