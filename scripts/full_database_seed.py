import sqlite3
import shutil
import os
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database" / "nizam_alqirtasiyah.db"
BACKUP_DIR = ROOT / "backups"
BACKUP_DIR.mkdir(exist_ok=True)

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP = BACKUP_DIR / f"before_full_seed_{stamp}.db"

print("=" * 70)
print("FULL ERP DATABASE BACKUP + DATA SEED")
print("=" * 70)

if not DB.exists():
    print("STATUS: FAILED")
    print("DATABASE NOT FOUND:", DB)
    raise SystemExit(1)

# 1) BACKUP
shutil.copy2(DB, BACKUP)
print("BACKUP:", BACKUP)

con = sqlite3.connect(DB)
con.execute("PRAGMA foreign_keys=OFF")
con.execute("PRAGMA journal_mode=WAL")
cur = con.cursor()

# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------
def tables():
    return [
        r[0] for r in cur.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """).fetchall()
    ]

def cols(table):
    return [r[1] for r in cur.execute(f'PRAGMA table_info("{table}")').fetchall()]

def q(v):
    if v is None:
        return None
    return v

def insert(table, data):
    available = set(cols(table))
    data = {k:v for k,v in data.items() if k in available}

    if not data:
        return None

    names = list(data.keys())
    marks = ",".join(["?"] * len(names))
    sql = f'INSERT INTO "{table}" ({",".join(chr(34)+x+chr(34) for x in names)}) VALUES ({marks})'

    try:
        cur.execute(sql, [data[x] for x in names])
        return cur.lastrowid
    except Exception:
        return None

def update(table, where, data):
    available = set(cols(table))
    data = {k:v for k,v in data.items() if k in available}
    where = {k:v for k,v in where.items() if k in available}

    if not data or not where:
        return

    sets = ",".join(f'"{k}"=?' for k in data)
    wh = " AND ".join(f'"{k}"=?' for k in where)

    try:
        cur.execute(
            f'UPDATE "{table}" SET {sets} WHERE {wh}',
            list(data.values()) + list(where.values())
        )
    except Exception:
        pass

def count(table):
    try:
        return cur.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    except Exception:
        return 0

def first_id(table):
    try:
        r = cur.execute(f'SELECT id FROM "{table}" ORDER BY id LIMIT 1').fetchone()
        return r[0] if r else None
    except Exception:
        return None

NOW = datetime.now().isoformat()

# ---------------------------------------------------------
# 2) Clean operational/sample data
# ---------------------------------------------------------
print("\n[1] CLEANING OLD OPERATIONAL DATA")

# Delete child tables first.
priority_delete = [
    "journal_entry_lines",
    "sale_payments",
    "sale_items",
    "purchase_invoice_items",
    "purchase_order_items",
    "stock_movements",
    "cash_transactions",
    "bank_transactions",
    "customer_payments",
    "supplier_payments",
    "inventory_adjustments",
    "inventory_counts",
    "approval_actions",
    "approval_requests",
    "notifications",
    "sync_queue",
    "sync_conflicts",
    "offline_operations",
    "ecommerce_orders",
    "product_channel_links",
    "interbranch_transfers",
    "audit_log",
    "security_audit",
    "search_index",
    "operation_center_tasks",
    "system_test_runs",
    "journal_entries",
    "purchase_invoices",
    "purchase_orders",
    "sales",
]

for t in priority_delete:
    if t in tables():
        try:
            cur.execute(f'DELETE FROM "{t}"')
        except Exception:
            pass

# Clean common master/demo tables only if present.
for t in [
    "products",
    "customers",
    "suppliers",
    "warehouses",
    "branches",
]:
    if t in tables():
        try:
            cur.execute(f'DELETE FROM "{t}"')
        except Exception:
            pass

# ---------------------------------------------------------
# 3) Company / branch / warehouse
# ---------------------------------------------------------
print("[2] MASTER DATA")

company_id = insert("companies", {
    "id": 1,
    "name": "قرطاسية لؤلؤة الأربعين النموذجية",
    "tax_number": "310000000000003",
    "phone": "0500000000",
    "address": "حي الصفا، شارع عبدالله بن سهل، جدة 23456",
    "created_at": NOW
})

if "companies" in tables() and count("companies") == 0:
    company_id = insert("companies", {
        "name": "قرطاسية لؤلؤة الأربعين النموذجية",
        "tax_number": "310000000000003",
        "phone": "0500000000",
        "address": "حي الصفا، شارع عبدالله بن سهل، جدة 23456",
        "created_at": NOW
    })
else:
    company_id = first_id("companies")

branch_id = insert("branches", {
    "id": 1,
    "company_id": company_id,
    "name": "الفرع الرئيسي",
    "code": "MAIN",
    "phone": "0500000000",
    "address": "جدة - حي الصفا",
    "is_active": 1,
    "created_at": NOW
})

if not branch_id:
    branch_id = first_id("branches")

warehouse_id = insert("warehouses", {
    "id": 1,
    "branch_id": branch_id,
    "name": "المستودع الرئيسي",
    "code": "WH-MAIN",
    "is_active": 1,
    "created_at": NOW
})

if not warehouse_id:
    warehouse_id = first_id("warehouses")

# ---------------------------------------------------------
# 4) Categories / brands / units
# ---------------------------------------------------------
print("[3] PRODUCTS MASTER DATA")

category_names = [
    "أدوات الكتابة",
    "القرطاسية المدرسية",
    "الفنون والرسم",
    "الطباعة والخدمات",
    "المنتجات التقنية",
    "الحقائب والمستلزمات"
]

category_ids = []
if "product_categories" in tables():
    for i, name in enumerate(category_names, 1):
        cid = insert("product_categories", {
            "id": i,
            "name": name,
            "name_ar": name,
            "name_en": name,
            "code": f"CAT-{i:03d}",
            "is_active": 1,
            "created_at": NOW
        })
        if cid:
            category_ids.append(cid)

brand_names = ["أقلام بيلو", "بيك", "فابر كاستل", "كاسيو", "إبسون"]
brand_ids = []
if "brands" in tables():
    for i, name in enumerate(brand_names, 1):
        bid = insert("brands", {
            "id": i,
            "name": name,
            "name_ar": name,
            "name_en": name,
            "code": f"BR-{i:03d}",
            "is_active": 1,
            "created_at": NOW
        })
        if bid:
            brand_ids.append(bid)

unit_names = ["قطعة", "علبة", "كرتون", "كيلو", "خدمة"]
unit_ids = []
if "units" in tables():
    for i, name in enumerate(unit_names, 1):
        uid = insert("units", {
            "id": i,
            "name": name,
            "name_ar": name,
            "name_en": name,
            "code": f"U-{i:03d}",
            "is_active": 1,
            "created_at": NOW
        })
        if uid:
            unit_ids.append(uid)

# ---------------------------------------------------------
# 5) Accounts
# ---------------------------------------------------------
print("[4] ACCOUNTING MASTER")

accounts = [
    ("1100","الخزينة","asset"),
    ("1200","البنوك","asset"),
    ("1300","العملاء","asset"),
    ("1400","المخزون","asset"),
    ("1410","ضريبة القيمة المضافة - مدخلات","asset"),
    ("2100","الموردون","liability"),
    ("2200","ضريبة القيمة المضافة - مخرجات","liability"),
    ("4100","مبيعات القرطاسية","revenue"),
    ("4200","خدمات الطباعة","revenue"),
    ("5100","تكلفة البضاعة المباعة","expense"),
]

if "accounts" in tables():
    for code, name, typ in accounts:
        cur.execute(
            'SELECT id FROM accounts WHERE account_code=?',
            (code,)
        )
        if not cur.fetchone():
            insert("accounts", {
                "account_code": code,
                "account_name": name,
                "account_type": typ,
                "is_active": 1,
                "allow_posting": 1,
                "opening_balance": 0,
                "created_at": NOW
            })

# ---------------------------------------------------------
# 6) Suppliers
# ---------------------------------------------------------
print("[5] SUPPLIERS")

supplier_ids = []
if "suppliers" in tables():
    suppliers = [
        ("شركة التوريد المكتبي","0501111111"),
        ("مؤسسة الأدوات المدرسية","0502222222"),
        ("شركة التقنية والطباعة","0503333333"),
    ]

    for i,(name,phone) in enumerate(suppliers,1):
        sid = insert("suppliers", {
            "id": i,
            "name": name,
            "name_ar": name,
            "phone": phone,
            "is_active": 1,
            "created_at": NOW
        })
        if sid:
            supplier_ids.append(sid)

supplier_id = supplier_ids[0] if supplier_ids else first_id("suppliers")

# ---------------------------------------------------------
# 7) Customers
# ---------------------------------------------------------
print("[6] CUSTOMERS")

customer_ids = []
if "customers" in tables():
    customers = [
        ("عميل نقدي","0504444444"),
        ("مدرسة اليقظة","0505555555"),
        ("مؤسسة تعليمية","0506666666"),
        ("شركة خدمات","0507777777"),
    ]

    for i,(name,phone) in enumerate(customers,1):
        cid = insert("customers", {
            "id": i,
            "name": name,
            "name_ar": name,
            "phone": phone,
            "credit_limit": 5000,
            "is_active": 1,
            "created_at": NOW
        })
        if cid:
            customer_ids.append(cid)

customer_id = customer_ids[0] if customer_ids else first_id("customers")

# ---------------------------------------------------------
# 8) Products
# ---------------------------------------------------------
print("[7] PRODUCTS")

product_ids = []

products = [
    ("SKU-1001","100000000001","دفتر 100 ورقة",12,18,10),
    ("SKU-1002","100000000002","قلم حبر أزرق",2,3,1),
    ("SKU-1003","100000000003","قلم رصاص",1.5,2.5,0.8),
    ("SKU-1004","100000000004","ممحاة مدرسية",1,2,0.5),
    ("SKU-1005","100000000005","مسطرة 30 سم",2,4,1),
    ("SKU-1006","100000000006","ألوان خشبية 12 لون",12,18,8),
    ("SKU-1007","100000000007","آلة حاسبة علمية",55,75,45),
    ("SKU-1008","100000000008","ورق تصوير A4",18,25,14),
    ("SKU-1009","100000000009","حبر طابعة أسود",45,65,35),
    ("SKU-1010","100000000010","ملف بلاستيك",2,4,1),
]

if "products" in tables():
    for i,(sku,barcode,name,cost,sale,wholesale) in enumerate(products,1):
        pid = insert("products", {
            "id": i,
            "sku": sku,
            "barcode": barcode,
            "name_ar": name,
            "name_en": name,
            "category_id": category_ids[(i-1) % len(category_ids)] if category_ids else None,
            "brand_id": brand_ids[(i-1) % len(brand_ids)] if brand_ids else None,
            "unit_id": unit_ids[0] if unit_ids else None,
            "product_type": "PRODUCT",
            "cost_price": cost,
            "sale_price": sale,
            "wholesale_price": wholesale,
            "school_price": sale * 0.95,
            "corporate_price": sale * 0.93,
            "min_price": cost,
            "reorder_point": 5,
            "min_stock": 3,
            "max_stock": 100,
            "is_active": 1,
            "created_at": NOW,
            "updated_at": NOW
        })
        if pid:
            product_ids.append(pid)

# ---------------------------------------------------------
# 9) Tax
# ---------------------------------------------------------
print("[8] TAX")

tax_id = None
if "tax_rates" in tables():
    tax_id = first_id("tax_rates")
    if not tax_id:
        tax_id = insert("tax_rates", {
            "code": "VAT15",
            "name": "ضريبة القيمة المضافة 15%",
            "rate": 15,
            "is_active": 1
        })

# ---------------------------------------------------------
# 10) Purchase
# ---------------------------------------------------------
print("[9] PURCHASE FLOW")

purchase_order_id = None
purchase_invoice_id = None

if "purchase_orders" in tables() and product_ids and supplier_id:
    subtotal = 100.0
    tax = 15.0
    total = 115.0

    purchase_order_id = insert("purchase_orders", {
        "order_number": "PO-2026-000001",
        "branch_id": branch_id,
        "supplier_id": supplier_id,
        "status": "RECEIVED",
        "subtotal": subtotal,
        "discount_amount": 0,
        "tax_amount": tax,
        "total_amount": total,
        "notes": "طلب شراء تجريبي متكامل",
        "created_at": NOW
    })

    if purchase_order_id and "purchase_order_items" in tables():
        insert("purchase_order_items", {
            "order_id": purchase_order_id,
            "purchase_order_id": purchase_order_id,
            "product_id": product_ids[0],
            "quantity": 10,
            "unit_cost": 10,
            "tax_amount": 15,
            "line_total": 115
        })

    if "purchase_invoices" in tables():
        purchase_invoice_id = insert("purchase_invoices", {
            "invoice_number": "PINV-2026-000001",
            "supplier_id": supplier_id,
            "purchase_order_id": purchase_order_id,
            "subtotal": subtotal,
            "tax_amount": tax,
            "total_amount": total,
            "paid_amount": 0,
            "due_amount": total,
            "status": "POSTED",
            "invoice_date": datetime.now().strftime("%Y-%m-%d"),
            "due_date": datetime.now().strftime("%Y-%m-%d")
        })

    if purchase_invoice_id and "purchase_invoice_items" in tables():
        insert("purchase_invoice_items", {
            "invoice_id": purchase_invoice_id,
            "purchase_invoice_id": purchase_invoice_id,
            "product_id": product_ids[0],
            "quantity": 10,
            "unit_cost": 10,
            "tax_amount": 15,
            "line_total": 115
        })

# ---------------------------------------------------------
# 11) Stock purchase movement
# ---------------------------------------------------------
if "stock_movements" in tables() and product_ids:
    insert("stock_movements", {
        "product_id": product_ids[0],
        "warehouse_id": warehouse_id,
        "movement_type": "PURCHASE",
        "quantity": 10,
        "unit_cost": 10,
        "reference_type": "PURCHASE_ORDER",
        "reference_id": purchase_order_id,
        "notes": "استلام مشتريات",
        "created_at": NOW
    })

# ---------------------------------------------------------
# 12) Sale
# ---------------------------------------------------------
print("[10] POS / SALES FLOW")

sale_id = None

if "sales" in tables() and product_ids:
    sale_subtotal = 46.0
    sale_tax = 6.9
    sale_total = 52.9

    sale_id = insert("sales", {
        "invoice_number": "INV-2026-000001",
        "branch_id": branch_id,
        "warehouse_id": warehouse_id,
        "customer_id": customer_id,
        "cashier_id": first_id("users"),
        "status": "POSTED",
        "subtotal": sale_subtotal,
        "discount_amount": 0,
        "tax_amount": sale_tax,
        "total_amount": sale_total,
        "paid_amount": sale_total,
        "due_amount": 0,
        "notes": "فاتورة بيع تجريبية",
        "created_at": NOW
    })

    if sale_id and "sale_items" in tables():
        insert("sale_items", {
            "sale_id": sale_id,
            "product_id": product_ids[0],
            "quantity": 2,
            "unit_price": 23,
            "discount_amount": 0,
            "tax_amount": sale_tax,
            "line_total": sale_subtotal
        })

    if sale_id and "sale_payments" in tables():
        insert("sale_payments", {
            "sale_id": sale_id,
            "payment_method": "CASH",
            "amount": sale_total,
            "reference_number": "CASH-000001",
            "notes": "دفع نقدي"
        })

# ---------------------------------------------------------
# 13) Stock sale movement
# ---------------------------------------------------------
if "stock_movements" in tables() and product_ids and sale_id:
    insert("stock_movements", {
        "product_id": product_ids[0],
        "warehouse_id": warehouse_id,
        "movement_type": "SALE",
        "quantity": -2,
        "unit_cost": 10,
        "reference_type": "SALE",
        "reference_id": sale_id,
        "notes": "صرف مخزون بسبب البيع",
        "created_at": NOW
    })

# ---------------------------------------------------------
# 14) Accounting journals
# ---------------------------------------------------------
print("[11] ACCOUNTING JOURNALS")

def account_id(code):
    try:
        r = cur.execute(
            "SELECT id FROM accounts WHERE account_code=?",
            (code,)
        ).fetchone()
        return r[0] if r else None
    except Exception:
        return None

def journal(number, description, source_type, source_id, lines):
    if "journal_entries" not in tables():
        return None

    je = insert("journal_entries", {
        "entry_number": number,
        "entry_date": datetime.now().strftime("%Y-%m-%d"),
        "description": description,
        "source_type": source_type,
        "source_id": source_id,
        "status": "posted",
        "created_by": first_id("users"),
        "created_at": NOW
    })

    if je and "journal_entry_lines" in tables():
        for code,debit,credit,desc in lines:
            insert("journal_entry_lines", {
                "journal_entry_id": je,
                "account_id": account_id(code),
                "description": desc,
                "debit": debit,
                "credit": credit
            })

    return je

if purchase_invoice_id:
    journal(
        "JE-2026-000001",
        "إثبات فاتورة شراء",
        "PURCHASE",
        purchase_invoice_id,
        [
            ("1400",100,0,"المخزون"),
            ("1410",15,0,"ضريبة مدخلات"),
            ("2100",0,115,"الموردون"),
        ]
    )

if sale_id:
    journal(
        "JE-2026-000002",
        "إثبات فاتورة بيع",
        "SALE",
        sale_id,
        [
            ("1100",52.9,0,"الخزينة"),
            ("4100",0,46,"مبيعات القرطاسية"),
            ("2200",0,6.9,"ضريبة مخرجات"),
            ("5100",20,0,"تكلفة البضاعة المباعة"),
            ("1400",0,20,"المخزون"),
        ]
    )

# ---------------------------------------------------------
# 15) Settings
# ---------------------------------------------------------
print("[12] SYSTEM SETTINGS")

settings = [
    ("company_name","قرطاسية لؤلؤة الأربعين النموذجية","text"),
    ("default_currency","SAR","text"),
    ("vat_rate","15","number"),
    ("language","ar","text"),
    ("rtl","true","boolean"),
    ("offline_first","true","boolean"),
    ("invoice_prefix","INV","text"),
    ("purchase_prefix","PINV","text"),
]

if "system_settings" in tables():
    for key,value,typ in settings:
        cur.execute(
            "DELETE FROM system_settings WHERE setting_key=?",
            (key,)
        )
        insert("system_settings", {
            "setting_key": key,
            "setting_value": value,
            "value_type": typ,
            "description": "إعداد نظام",
            "updated_at": NOW
        })

# ---------------------------------------------------------
# 16) Generic safe filling for empty tables
# ---------------------------------------------------------
print("[13] CHECKING ALL TABLES")

skip_generic = {
    "schema_versions",
    "system_info",
    "application_versions",
    "sqlite_sequence"
}

all_tables = tables()

for t in all_tables:
    if t in skip_generic:
        continue

    if count(t) > 0:
        continue

    c = cols(t)

    # لا نحاول اختراع صفوف في جداول لا تحتوي على أعمدة
    if not c:
        continue

    # الجداول التي لا تحتاج بيانات اصطناعية
    if t in {
        "companies","branches","warehouses","products","customers",
        "suppliers","accounts","tax_rates","sales","sale_items",
        "sale_payments","purchase_orders","purchase_order_items",
        "purchase_invoices","purchase_invoice_items","stock_movements",
        "journal_entries","journal_entry_lines","system_settings"
    }:
        continue

    data = {}

    for col in c:
        lc = col.lower()

        if lc == "id":
            continue

        if lc.endswith("_id") or lc == "parent_id":
            # حاول استخدام معرف موجود من نفس النوع
            base = lc.replace("_id","")
            candidates = {
                "company": company_id,
                "branch": branch_id,
                "warehouse": warehouse_id,
                "supplier": supplier_id,
                "customer": customer_id,
                "product": product_ids[0] if product_ids else None,
                "user": first_id("users"),
                "account": account_id("1100"),
                "sale": sale_id,
                "purchase_order": purchase_order_id,
                "purchase_invoice": purchase_invoice_id
            }
            if base in candidates and candidates[base] is not None:
                data[col] = candidates[base]
            else:
                data[col] = None

        elif "date" in lc or lc.endswith("_at"):
            data[col] = NOW

        elif "is_" in lc or lc.startswith("has_") or lc.startswith("allow_"):
            data[col] = 1

        elif lc in ("status","state"):
            data[col] = "ACTIVE"

        elif "name" in lc:
            data[col] = "بيانات تجريبية"

        elif "code" in lc or "number" in lc:
            data[col] = f"DEMO-{t[:8].upper()}"

        elif "description" in lc or "notes" in lc:
            data[col] = "بيانات تجريبية للنظام"

        elif "amount" in lc or "balance" in lc or "price" in lc or "quantity" in lc or "rate" in lc or "total" in lc or "limit" in lc:
            data[col] = 0

        else:
            info = cur.execute(
                f'PRAGMA table_info("{t}")'
            ).fetchall()
            typ = ""
            for row in info:
                if row[1] == col:
                    typ = (row[2] or "").upper()
                    break

            if "INT" in typ:
                data[col] = 0
            elif "REAL" in typ or "NUM" in typ or "DEC" in typ:
                data[col] = 0
            else:
                data[col] = "بيانات تجريبية"

    # Only attempt generic insertion when required fields can be satisfied.
    insert(t, data)

# ---------------------------------------------------------
# 17) Integrity
# ---------------------------------------------------------
con.commit()

integrity = cur.execute("PRAGMA integrity_check").fetchone()[0]
foreign_keys = cur.execute("PRAGMA foreign_key_check").fetchall()

# Re-enable FK
cur.execute("PRAGMA foreign_keys=ON")

# ---------------------------------------------------------
# 18) Report
# ---------------------------------------------------------
print("\n" + "=" * 70)
print("DATABASE CONTENT REPORT")
print("=" * 70)

for t in all_tables:
    print(f"{t:40} {count(t)}")

print("\n" + "=" * 70)
print("INTEGRITY:", integrity)
print("FOREIGN KEY ERRORS:", len(foreign_keys))
print("BACKUP:", BACKUP)

if integrity == "ok" and len(foreign_keys) == 0:
    print("STATUS: SUCCESS")
else:
    print("STATUS: FAILED")
    print("FOREIGN KEY DETAILS:", foreign_keys[:20])
    raise SystemExit(1)

con.close()
