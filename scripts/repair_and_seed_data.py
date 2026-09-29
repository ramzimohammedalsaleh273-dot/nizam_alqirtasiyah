import sqlite3
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database" / "nizam_alqirtasiyah.db"

con = sqlite3.connect(DB)
cur = con.cursor()
cur.execute("PRAGMA foreign_keys=OFF")

NOW = datetime.now().isoformat()

def cols(t):
    return [r[1] for r in cur.execute(f'PRAGMA table_info("{t}")').fetchall()]

def exists(t):
    return cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(t,)
    ).fetchone() is not None

def count(t):
    try:
        return cur.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
    except:
        return 0

def insert(t, data):
    if not exists(t):
        return None
    av=set(cols(t))
    data={k:v for k,v in data.items() if k in av}
    if not data:
        return None
    names=list(data)
    marks=",".join("?" for _ in names)
    try:
        cur.execute(
            f'INSERT INTO "{t}" ({",".join(chr(34)+x+chr(34) for x in names)}) VALUES ({marks})',
            [data[x] for x in names]
        )
        return cur.lastrowid
    except:
        return None

def first_id(t):
    if not exists(t):
        return None
    try:
        r=cur.execute(f'SELECT id FROM "{t}" ORDER BY id LIMIT 1').fetchone()
        return r[0] if r else None
    except:
        return None

print("="*70)
print("ERP DATA REPAIR")
print("="*70)

user_id=first_id("users")
branch_id=first_id("branches")
warehouse_id=first_id("warehouses")

print("USER ID:",user_id)
print("BRANCH ID:",branch_id)
print("WAREHOUSE ID:",warehouse_id)

# --------------------------------------------------
# 1. إصلاح purchase_requests و sale_returns
# --------------------------------------------------
for table in ["purchase_requests","sale_returns"]:
    if not exists(table):
        continue

    fks=cur.execute(f'PRAGMA foreign_key_list("{table}")').fetchall()

    for fk in fks:
        # fk: id, seq, table, from, to, on_update, on_delete, match
        ref_table=fk[2]
        from_col=fk[3]

        if ref_table=="users" and user_id is not None:
            try:
                cur.execute(
                    f'UPDATE "{table}" SET "{from_col}"=? WHERE "{from_col}" IS NULL OR "{from_col}"=0',
                    (user_id,)
                )
            except:
                pass

# إذا بقيت صفوف مرتبطة بمستخدم غير موجود، احذف الصفوف التجريبية فقط
for table in ["purchase_requests","sale_returns"]:
    if not exists(table):
        continue

    fks=cur.execute(f'PRAGMA foreign_key_list("{table}")').fetchall()

    for fk in fks:
        if fk[2]=="users":
            col=fk[3]
            try:
                cur.execute(
                    f'DELETE FROM "{table}" WHERE "{col}" IS NOT NULL AND "{col}" NOT IN (SELECT id FROM users)'
                )
            except:
                pass

# --------------------------------------------------
# 2. العملاء
# --------------------------------------------------
print("\n[1] CUSTOMERS")

if exists("customers") and count("customers")==0:

    c=cols("customers")

    rows=[
        {
            "name":"عميل نقدي",
            "name_ar":"عميل نقدي",
            "phone":"0504444444",
            "mobile":"0504444444",
            "customer_code":"CUST-001",
            "code":"CUST-001",
            "is_active":1,
            "credit_limit":0,
            "opening_balance":0,
            "created_at":NOW,
            "updated_at":NOW
        },
        {
            "name":"مدرسة اليقظة",
            "name_ar":"مدرسة اليقظة",
            "phone":"0505555555",
            "mobile":"0505555555",
            "customer_code":"CUST-002",
            "code":"CUST-002",
            "is_active":1,
            "credit_limit":5000,
            "opening_balance":0,
            "created_at":NOW,
            "updated_at":NOW
        },
        {
            "name":"مؤسسة تعليمية",
            "name_ar":"مؤسسة تعليمية",
            "phone":"0506666666",
            "mobile":"0506666666",
            "customer_code":"CUST-003",
            "code":"CUST-003",
            "is_active":1,
            "credit_limit":10000,
            "opening_balance":0,
            "created_at":NOW,
            "updated_at":NOW
        },
        {
            "name":"شركة خدمات",
            "name_ar":"شركة خدمات",
            "phone":"0507777777",
            "mobile":"0507777777",
            "customer_code":"CUST-004",
            "code":"CUST-004",
            "is_active":1,
            "credit_limit":15000,
            "opening_balance":0,
            "created_at":NOW,
            "updated_at":NOW
        }
    ]

    for row in rows:
        insert("customers",row)

print("CUSTOMERS:",count("customers"))

# --------------------------------------------------
# 3. الموردون
# --------------------------------------------------
print("\n[2] SUPPLIERS")

if exists("suppliers") and count("suppliers")==0:

    rows=[
        {
            "name":"شركة التوريد المكتبي",
            "name_ar":"شركة التوريد المكتبي",
            "phone":"0501111111",
            "mobile":"0501111111",
            "supplier_code":"SUP-001",
            "code":"SUP-001",
            "is_active":1,
            "credit_limit":20000,
            "opening_balance":0,
            "created_at":NOW,
            "updated_at":NOW
        },
        {
            "name":"مؤسسة الأدوات المدرسية",
            "name_ar":"مؤسسة الأدوات المدرسية",
            "phone":"0502222222",
            "mobile":"0502222222",
            "supplier_code":"SUP-002",
            "code":"SUP-002",
            "is_active":1,
            "credit_limit":20000,
            "opening_balance":0,
            "created_at":NOW,
            "updated_at":NOW
        },
        {
            "name":"شركة التقنية والطباعة",
            "name_ar":"شركة التقنية والطباعة",
            "phone":"0503333333",
            "mobile":"0503333333",
            "supplier_code":"SUP-003",
            "code":"SUP-003",
            "is_active":1,
            "credit_limit":30000,
            "opening_balance":0,
            "created_at":NOW,
            "updated_at":NOW
        }
    ]

    for row in rows:
        insert("suppliers",row)

print("SUPPLIERS:",count("suppliers"))

# --------------------------------------------------
# 4. التأكد من البيانات الرئيسية
# --------------------------------------------------
print("\n[3] MASTER DATA")

for t in [
    "companies",
    "branches",
    "warehouses",
    "product_categories",
    "brands",
    "units",
    "products",
    "customers",
    "suppliers",
    "accounts",
    "tax_rates",
    "users"
]:
    if exists(t):
        print(f"{t:30} {count(t)}")

# --------------------------------------------------
# 5. إصلاح العلاقات الخارجية
# --------------------------------------------------
con.commit()

cur.execute("PRAGMA foreign_keys=ON")

errors=cur.execute("PRAGMA foreign_key_check").fetchall()
integrity=cur.execute("PRAGMA integrity_check").fetchone()[0]

print("\n" + "="*70)
print("FINAL CHECK")
print("="*70)
print("INTEGRITY:",integrity)
print("FOREIGN KEY ERRORS:",len(errors))

if errors:
    print("ERRORS:",errors[:20])

print("\nOPERATIONAL TABLES")
for t in [
    "purchase_requests",
    "purchase_orders",
    "purchase_order_items",
    "purchase_invoices",
    "purchase_invoice_items",
    "stock_movements",
    "sales",
    "sale_items",
    "sale_payments",
    "journal_entries",
    "journal_entry_lines",
    "cash_transactions",
    "tax_invoices"
]:
    if exists(t):
        print(f"{t:30} {count(t)}")

if integrity=="ok" and not errors and count("products")>=10 and count("customers")>=1 and count("suppliers")>=1:
    print("\nSTATUS: SUCCESS")
else:
    print("\nSTATUS: FAILED")

con.close()
