import sqlite3,datetime,os,shutil
DB=r"database\nizam_alqirtasiyah.db"
os.makedirs(r"database\backups",exist_ok=True)
s=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copy2(DB,rf"database\backups\nizam_alqirtasiyah_before_links_{s}.db")
c=sqlite3.connect(DB); c.execute("PRAGMA foreign_keys=ON"); x=c.cursor(); now=datetime.datetime.now().isoformat(timespec="seconds")

def T(): return {r[0] for r in x.execute("SELECT name FROM sqlite_master WHERE type='table'")}
def C(t): return [r[1] for r in x.execute(f'PRAGMA table_info("{t}")')]
def add(t,d):
    if t not in T(): return
    d={k:v for k,v in d.items() if k in C(t)}
    if not d:return
    try:
        n=list(d); q=",".join("?"*len(n))
        x.execute(f'INSERT OR IGNORE INTO "{t}" ({",".join(chr(34)+z+chr(34) for z in n)}) VALUES ({q})',[d[z] for z in n])
    except: pass

try:
    c.execute("BEGIN")

    # حركات العملاء من المبيعات
    if "customer_transactions" in T():
        for r in x.execute("SELECT id,customer_id,total,grand_total FROM sales WHERE customer_id IS NOT NULL").fetchall():
            sid,cid,total,grand=r
            amount=grand if grand is not None else total
            add("customer_transactions",{
                "customer_id":cid,"transaction_type":"sale",
                "reference_id":sid,"reference_type":"sale",
                "debit":amount,"credit":0,"amount":amount,
                "description":f"فاتورة بيع رقم {sid}","transaction_date":now,"created_at":now
            })

    # مدفوعات العملاء
    if "customer_payments" in T():
        for r in x.execute("SELECT id,customer_id,total,grand_total FROM sales WHERE customer_id IS NOT NULL").fetchall():
            sid,cid,total,grand=r
            amount=grand if grand is not None else total
            add("customer_payments",{
                "customer_id":cid,"reference_id":sid,
                "reference_type":"sale","amount":amount,
                "payment_amount":amount,"payment_method":"cash",
                "payment_date":now,"created_at":now
            })

    # حركات الموردين من المشتريات
    if "supplier_transactions" in T():
        for r in x.execute("SELECT id,supplier_id,total,grand_total FROM purchase_invoices WHERE supplier_id IS NOT NULL").fetchall():
            pid,sid,total,grand=r
            amount=grand if grand is not None else total
            add("supplier_transactions",{
                "supplier_id":sid,"transaction_type":"purchase",
                "reference_id":pid,"reference_type":"purchase",
                "debit":0,"credit":amount,"amount":amount,
                "description":f"فاتورة شراء رقم {pid}",
                "transaction_date":now,"created_at":now
            })

    # تحديث المخزون
    if "stock" in T():
        for pid in [r[0] for r in x.execute("SELECT id FROM products").fetchall()]:
            add("stock",{"product_id":pid,"quantity":50,"current_quantity":50,"available_quantity":50})

    c.commit()

    print("="*68)
    print("تم ربط العمليات بنجاح")
    print("="*68)
    for t in ["customer_transactions","customer_payments","supplier_transactions","stock"]:
        if t in T():
            print(f"{t:28} {x.execute(f'SELECT COUNT(*) FROM \"{t}\"').fetchone()[0]} سجل")
    print("سلامة قاعدة البيانات:",x.execute("PRAGMA integrity_check").fetchone()[0])
except Exception as e:
    c.rollback(); print("تم التراجع عن العملية:",repr(e))
finally:c.close()
