import sqlite3, os, shutil, datetime

DB=r"database\nizam_alqirtasiyah.db"
os.makedirs(r"database\backups",exist_ok=True)
stamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup=rf"database\backups\nizam_alqirtasiyah_before_relations_{stamp}.db"
shutil.copy2(DB,backup)

con=sqlite3.connect(DB)
con.execute("PRAGMA foreign_keys=ON")
cur=con.cursor()

def tabs():
    return {r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )}

def cols(t):
    return [r[1] for r in cur.execute(f'PRAGMA table_info("{t}")')]

def add(t,d):
    if t not in tabs(): return 0
    c=cols(t); d={k:v for k,v in d.items() if k in c}
    if not d:return 0
    info=cur.execute(f'PRAGMA table_info("{t}")').fetchall()
    for r in info:
        if r[3] and r[4] is None and r[5]==0 and r[1] not in d:
            return 0
    try:
        n=list(d); v=[d[x] for x in n]
        q=",".join("?" for _ in n)
        cur.execute(
            f'INSERT OR IGNORE INTO "{t}" ({",".join(chr(34)+x+chr(34) for x in n)}) VALUES ({q})',v)
        return cur.rowcount
    except:return 0

def c(t):
    return cur.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]

now=datetime.datetime.now().isoformat(timespec="seconds")

try:
    con.execute("BEGIN")

    T=tabs()

    # ---------------------------------------------------------
    # 1 ـ ربط المنتجات بالوحدات
    # ---------------------------------------------------------
    if "product_units" in T and "products" in T and "units" in T:
        uid=cur.execute("SELECT id FROM units ORDER BY id LIMIT 1").fetchone()
        uid=uid[0] if uid else None
        if uid:
            for pid, in cur.execute("SELECT id FROM products ORDER BY id").fetchall():
                add("product_units",{
                    "product_id":pid,
                    "unit_id":uid,
                    "conversion_factor":1,
                    "factor":1,
                    "is_default":1,
                    "is_active":1,
                    "created_at":now
                })

    # ---------------------------------------------------------
    # 2 ـ مواقع المستودع
    # ---------------------------------------------------------
    if "warehouse_zones" in T:
        add("warehouse_zones",{
            "name":"المنطقة الرئيسية","zone_name":"المنطقة الرئيسية",
            "code":"ZONE-01","is_active":1,"created_at":now
        })

    zone=cur.execute("SELECT id FROM warehouse_zones ORDER BY id LIMIT 1").fetchone() if "warehouse_zones" in T else None
    zone=zone[0] if zone else None

    if "warehouse_aisles" in T:
        for i in range(1,4):
            add("warehouse_aisles",{
                "name":f"الممر {i}","aisle_name":f"الممر {i}",
                "code":f"A-{i:02}","warehouse_zone_id":zone,
                "zone_id":zone,"is_active":1,"created_at":now
            })

    aisle=cur.execute("SELECT id FROM warehouse_aisles ORDER BY id LIMIT 1").fetchone() if "warehouse_aisles" in T else None
    aisle=aisle[0] if aisle else None

    if "warehouse_shelves" in T:
        for i in range(1,6):
            add("warehouse_shelves",{
                "name":f"الرف {i}","shelf_name":f"الرف {i}",
                "code":f"S-{i:02}","aisle_id":aisle,
                "warehouse_aisle_id":aisle,"is_active":1,"created_at":now
            })

    shelf=cur.execute("SELECT id FROM warehouse_shelves ORDER BY id LIMIT 1").fetchone() if "warehouse_shelves" in T else None
    shelf=shelf[0] if shelf else None

    if "warehouse_bins" in T:
        for i in range(1,11):
            add("warehouse_bins",{
                "name":f"الصندوق {i}","bin_name":f"الصندوق {i}",
                "code":f"B-{i:03}","shelf_id":shelf,
                "warehouse_shelf_id":shelf,"is_active":1,"created_at":now
            })

    # ---------------------------------------------------------
    # 3 ـ ربط المنتجات بالموردين
    # ---------------------------------------------------------
    if "supplier_products" in T:
        suppliers=cur.execute("SELECT id FROM suppliers ORDER BY id").fetchall()
        products=cur.execute("SELECT id FROM products ORDER BY id").fetchall()
        for i,(pid,) in enumerate(products):
            if suppliers:
                sid=suppliers[i % len(suppliers)][0]
                add("supplier_products",{
                    "supplier_id":sid,"product_id":pid,
                    "is_primary":1,"is_active":1,
                    "created_at":now
                })

    # ---------------------------------------------------------
    # 4 ـ أسعار الموردين
    # ---------------------------------------------------------
    if "supplier_prices" in T and "supplier_products" in T:
        rows=cur.execute("SELECT supplier_id,product_id FROM supplier_products").fetchall()
        for sid,pid in rows:
            prod=cur.execute(
                "SELECT COALESCE(cost_price,purchase_price,0) FROM products WHERE id=?",(pid,)
            ).fetchone()
            price=float(prod[0] or 0) if prod else 0
            add("supplier_prices",{
                "supplier_id":sid,"product_id":pid,
                "price":price,"unit_price":price,
                "currency":"YER","is_active":1,
                "created_at":now
            })

    # ---------------------------------------------------------
    # 5 ـ عناوين العملاء
    # ---------------------------------------------------------
    if "customer_addresses" in T:
        for cid,name in cur.execute("SELECT id,name FROM customers ORDER BY id").fetchall():
            add("customer_addresses",{
                "customer_id":cid,
                "address_type":"primary",
                "address":"اليمن",
                "city":"اليمن",
                "is_default":1,
                "is_active":1,
                "created_at":now
            })

    # ---------------------------------------------------------
    # 6 ـ حدود ائتمان العملاء
    # ---------------------------------------------------------
    if "customer_credit_limits" in T:
        for cid, in cur.execute("SELECT id FROM customers").fetchall():
            add("customer_credit_limits",{
                "customer_id":cid,
                "credit_limit":100000,
                "current_balance":0,
                "available_credit":100000,
                "is_active":1,
                "created_at":now
            })

    # ---------------------------------------------------------
    # 7 ـ ملاحظات العملاء
    # ---------------------------------------------------------
    if "customer_notes" in T:
        for cid,name in cur.execute("SELECT id,name FROM customers").fetchall():
            add("customer_notes",{
                "customer_id":cid,
                "note":"عميل مسجل في نظام القرطاسية",
                "notes":"عميل مسجل في نظام القرطاسية",
                "created_at":now
            })

    # ---------------------------------------------------------
    # 8 ـ تقييم الموردين
    # ---------------------------------------------------------
    if "supplier_evaluations" in T:
        for sid,name in cur.execute("SELECT id,name FROM suppliers").fetchall():
            add("supplier_evaluations",{
                "supplier_id":sid,
                "quality_score":5,
                "delivery_score":5,
                "price_score":5,
                "overall_score":5,
                "notes":"تقييم ابتدائي",
                "created_at":now
            })

    # ---------------------------------------------------------
    # 9 ـ عروض المنتجات
    # ---------------------------------------------------------
    if "promotion_items" in T:
        for pid, in cur.execute("SELECT id FROM products LIMIT 20").fetchall():
            add("promotion_items",{
                "product_id":pid,
                "discount_percent":5,
                "discount_percentage":5,
                "is_active":1,
                "created_at":now
            })

    # ---------------------------------------------------------
    # 10 ـ خطوات سير العمل
    # ---------------------------------------------------------
    if "workflow_steps" in T:
        workflows=cur.execute("SELECT id FROM workflows ORDER BY id").fetchall()
        for wid, in workflows:
            for i,name in enumerate(["إنشاء الطلب","المراجعة","الموافقة","التنفيذ"],1):
                add("workflow_steps",{
                    "workflow_id":wid,
                    "step_number":i,
                    "sequence":i,
                    "name":name,
                    "step_name":name,
                    "is_required":1,
                    "is_active":1,
                    "created_at":now
                })

    # ---------------------------------------------------------
    # 11 ـ حسابات الولاء للعملاء
    # ---------------------------------------------------------
    if "loyalty_accounts" in T:
        for cid,name in cur.execute("SELECT id,name FROM customers").fetchall():
            add("loyalty_accounts",{
                "customer_id":cid,
                "points":0,
                "balance":0,
                "is_active":1,
                "created_at":now
            })

    # ---------------------------------------------------------
    # 12 ـ معلومات تحليلية أولية
    # ---------------------------------------------------------
    if "analytics_snapshots" in T:
        add("analytics_snapshots",{
            "snapshot_date":now,
            "date":now[:10],
            "products_count":c("products") if "products" in T else 0,
            "customers_count":c("customers") if "customers" in T else 0,
            "suppliers_count":c("suppliers") if "suppliers" in T else 0,
            "created_at":now
        })

    con.commit()

    print()
    print("="*72)
    print("تمت المرحلة الثانية بنجاح")
    print("="*72)
    print("النسخة الاحتياطية:",backup)
    print("عدد الجداول:",len(T))
    print()
    for t in [
        "product_units","warehouse_aisles","warehouse_shelves",
        "warehouse_bins","customer_addresses","customer_credit_limits",
        "customer_notes","supplier_products","supplier_prices",
        "supplier_evaluations","promotion_items","loyalty_accounts",
        "workflow_steps","analytics_snapshots"
    ]:
        if t in T:
            print(f"{t:28} {c(t)} سجل")

    empty=[t for t in T if c(t)==0]
    print()
    print("الجداول الفارغة المتبقية:",len(empty))
    print(", ".join(sorted(empty)))
    print()
    print("سلامة قاعدة البيانات:",cur.execute("PRAGMA integrity_check").fetchone()[0])

except Exception as e:
    con.rollback()
    print("حدث خطأ وتم التراجع عن العملية.")
    print(repr(e))
finally:
    con.close()
