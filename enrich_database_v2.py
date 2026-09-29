import sqlite3,os,shutil,datetime

DB=r"database\nizam_alqirtasiyah.db"
os.makedirs(r"database\backups",exist_ok=True)
stamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup=rf"database\backups\nizam_alqirtasiyah_before_enrichment_{stamp}.db"
shutil.copy2(DB,backup)

c=sqlite3.connect(DB)
c.execute("PRAGMA foreign_keys=ON")
x=c.cursor()
now=datetime.datetime.now().isoformat(timespec="seconds")

def T():
    return {r[0] for r in x.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}

def C(t):
    return [r[1] for r in x.execute(f'PRAGMA table_info("{t}")')]

def add(t,d):
    if t not in T(): return 0
    cc=C(t)
    d={k:v for k,v in d.items() if k in cc}
    if not d:return 0
    try:
        n=list(d); q=",".join("?"*len(n))
        x.execute(f'INSERT OR IGNORE INTO "{t}" ({",".join(chr(34)+z+chr(34) for z in n)}) VALUES ({q})',[d[z] for z in n])
        return x.rowcount
    except:return 0

try:
    c.execute("BEGIN")

    # وحدات المنتجات
    if "product_units" in T():
        uid=x.execute("SELECT id FROM units ORDER BY id LIMIT 1").fetchone()
        if uid:
            for (pid,) in x.execute("SELECT id FROM products").fetchall():
                add("product_units",{"product_id":pid,"unit_id":uid[0],"conversion_factor":1,"is_default":1,"is_active":1,"created_at":now})

    # ربط المنتجات بالموردين
    if "supplier_products" in T():
        ss=x.execute("SELECT id FROM suppliers ORDER BY id").fetchall()
        ps=x.execute("SELECT id,cost_price FROM products ORDER BY id").fetchall()
        for i,(pid,cost) in enumerate(ps):
            if ss:
                add("supplier_products",{"supplier_id":ss[i%len(ss)][0],"product_id":pid,"is_primary":1,"is_active":1,"created_at":now})

    # أسعار الموردين
    if "supplier_prices" in T() and "supplier_products" in T():
        for sid,pid in x.execute("SELECT supplier_id,product_id FROM supplier_products").fetchall():
            r=x.execute("SELECT cost_price FROM products WHERE id=?",(pid,)).fetchone()
            price=r[0] if r else 0
            add("supplier_prices",{"supplier_id":sid,"product_id":pid,"price":price,"unit_price":price,"currency":"YER","is_active":1,"created_at":now})

    # عناوين العملاء
    if "customer_addresses" in T():
        for (cid,) in x.execute("SELECT id FROM customers").fetchall():
            add("customer_addresses",{"customer_id":cid,"address_type":"primary","address":"اليمن","city":"اليمن","is_default":1,"is_active":1,"created_at":now})

    # حدود الائتمان
    if "customer_credit_limits" in T():
        for (cid,) in x.execute("SELECT id FROM customers").fetchall():
            add("customer_credit_limits",{"customer_id":cid,"credit_limit":100000,"current_balance":0,"available_credit":100000,"is_active":1,"created_at":now})

    # ملاحظات العملاء
    if "customer_notes" in T():
        for (cid,) in x.execute("SELECT id FROM customers").fetchall():
            add("customer_notes",{"customer_id":cid,"note":"عميل مسجل في نظام القرطاسية","notes":"عميل مسجل في نظام القرطاسية","created_at":now})

    # تقييم الموردين
    if "supplier_evaluations" in T():
        for (sid,) in x.execute("SELECT id FROM suppliers").fetchall():
            add("supplier_evaluations",{"supplier_id":sid,"quality_score":5,"delivery_score":5,"price_score":5,"overall_score":5,"notes":"تقييم ابتدائي","created_at":now})

    # حسابات الولاء
    if "loyalty_accounts" in T():
        for (cid,) in x.execute("SELECT id FROM customers").fetchall():
            add("loyalty_accounts",{"customer_id":cid,"points":0,"balance":0,"is_active":1,"created_at":now})

    # خطوات سير العمل
    if "workflow_steps" in T():
        for (wid,) in x.execute("SELECT id FROM workflows").fetchall():
            for i,n in enumerate(["إنشاء الطلب","المراجعة","الموافقة","التنفيذ"],1):
                add("workflow_steps",{"workflow_id":wid,"step_number":i,"sequence":i,"name":n,"step_name":n,"is_required":1,"is_active":1,"created_at":now})

    c.commit()

    print()
    print("="*65)
    print("تم الإثراء بنجاح")
    print("="*65)
    print("النسخة الاحتياطية:",backup)

    for t in ["products","product_units","supplier_products","supplier_prices","customer_addresses","customer_credit_limits","customer_notes","supplier_evaluations","loyalty_accounts","workflow_steps"]:
        if t in T():
            print(f"{t:28} {x.execute(f'SELECT COUNT(*) FROM \"{t}\"').fetchone()[0]} سجل")

    print()
    print("سلامة قاعدة البيانات:",x.execute("PRAGMA integrity_check").fetchone()[0])

except Exception as e:
    c.rollback()
    print("تم التراجع عن العملية بسبب خطأ:")
    print(repr(e))
finally:
    c.close()
