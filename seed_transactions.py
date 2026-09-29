import sqlite3,shutil,os,datetime

DB=r"database\nizam_alqirtasiyah.db"
os.makedirs(r"database\backups",exist_ok=True)
stamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copy2(DB,rf"database\backups\nizam_alqirtasiyah_before_transactions_{stamp}.db")

c=sqlite3.connect(DB)
c.execute("PRAGMA foreign_keys=ON")
x=c.cursor()
now=datetime.datetime.now().isoformat(timespec="seconds")

def cols(t): return [r[1] for r in x.execute(f'PRAGMA table_info("{t}")')]
def tables(): return {r[0] for r in x.execute("SELECT name FROM sqlite_master WHERE type='table'")}
def add(t,d):
    if t not in tables(): return
    cc=cols(t); d={k:v for k,v in d.items() if k in cc}
    if not d:return
    try:
        n=list(d); q=",".join("?"*len(n))
        x.execute(f'INSERT OR IGNORE INTO "{t}" ({",".join(chr(34)+z+chr(34) for z in n)}) VALUES ({q})',[d[z] for z in n])
    except: pass

try:
    c.execute("BEGIN")

    products=x.execute("SELECT id,cost_price,sale_price FROM products ORDER BY id LIMIT 10").fetchall()
    customers=x.execute("SELECT id FROM customers ORDER BY id LIMIT 10").fetchall()
    suppliers=x.execute("SELECT id FROM suppliers ORDER BY id LIMIT 5").fetchall()

    # تحديث المخزون الحالي للمنتجات
    if "stock" in tables():
        for pid,cost,sale in products:
            add("stock",{"product_id":pid,"quantity":50,"current_quantity":50,"available_quantity":50,"min_stock":5,"max_stock":100})

    # إنشاء عمليات بيع تجريبية مترابطة فقط إذا كانت الجداول تدعمها
    if "sales" in tables() and "sale_items" in tables() and customers:
        for i,(pid,cost,sale) in enumerate(products[:4],1):
            cid=customers[(i-1)%len(customers)][0]
            add("sales",{
                "invoice_number":f"SALE-SEED-{i:03}",
                "customer_id":cid,
                "subtotal":float(sale or 0),
                "total":float(sale or 0),
                "grand_total":float(sale or 0),
                "paid_amount":float(sale or 0),
                "status":"completed",
                "payment_status":"paid",
                "sale_date":now,
                "created_at":now
            })

    # إنشاء عمليات شراء تجريبية
    if "purchase_invoices" in tables() and suppliers:
        for i,(pid,cost,sale) in enumerate(products[:3],1):
            sid=suppliers[(i-1)%len(suppliers)][0]
            add("purchase_invoices",{
                "invoice_number":f"PUR-SEED-{i:03}",
                "supplier_id":sid,
                "subtotal":float(cost or 0)*10,
                "total":float(cost or 0)*10,
                "grand_total":float(cost or 0)*10,
                "paid_amount":float(cost or 0)*10,
                "status":"paid",
                "payment_status":"paid",
                "invoice_date":now,
                "created_at":now
            })

    c.commit()

    print("="*65)
    print("تمت مرحلة العمليات الأساسية بنجاح")
    print("="*65)
    for t in ["sales","sale_items","sale_payments","purchase_invoices","purchase_invoice_items","stock","customer_transactions","customer_payments"]:
        if t in tables():
            print(f"{t:28} {x.execute(f'SELECT COUNT(*) FROM \"{t}\"').fetchone()[0]} سجل")
    print()
    print("سلامة قاعدة البيانات:",x.execute("PRAGMA integrity_check").fetchone()[0])

except Exception as e:
    c.rollback()
    print("تم التراجع:",repr(e))
finally:
    c.close()
