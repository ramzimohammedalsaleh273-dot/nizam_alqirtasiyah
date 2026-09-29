import sqlite3, os, shutil, datetime, random

BASE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB=os.path.join(BASE,"database","nizam_alqirtasiyah.db")
BACK=os.path.join(BASE,"backups")
os.makedirs(BACK,exist_ok=True)

stamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup=os.path.join(BACK,f"before_complete_operational_seed_{stamp}.db")
shutil.copy2(DB,backup)

con=sqlite3.connect(DB)
con.execute("PRAGMA foreign_keys=ON")
cur=con.cursor()

def cols(t):
    return [r[1] for r in cur.execute(f'PRAGMA table_info("{t}")')]

def exists(t):
    return cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None

def ins(t,data):
    if not exists(t): return None
    c=cols(t)
    d={k:v for k,v in data.items() if k in c}
    if not d:return None
    ks=list(d); qs=",".join("?" for _ in ks)
    cur.execute(f'INSERT INTO "{t}" ({",".join(ks)}) VALUES ({qs})',tuple(d[k] for k in ks))
    return cur.lastrowid

def upd(t,idv,data):
    if not exists(t): return
    c=cols(t)
    d={k:v for k,v in data.items() if k in c}
    if not d:return
    cur.execute(f'UPDATE "{t}" SET '+",".join(f'"{k}"=?' for k in d)+f' WHERE id=?',tuple(d.values())+(idv,))

def first(t):
    if not exists(t): return None
    r=cur.execute(f'SELECT id FROM "{t}" ORDER BY id LIMIT 1').fetchone()
    return r[0] if r else None

now=datetime.datetime.now().isoformat(sep=" ",timespec="seconds")

try:
    # =========================================================
    # 1) الشركة
    # =========================================================
    company=first("companies")
    if not company:
        company=ins("companies",{
            "name":"قرطاسية لؤلؤة الأربعين النموذجية",
            "tax_number":"310000000000003",
            "phone":"0500000000",
            "address":"حي الصفا، شارع عبدالله بن سهل، جدة 23456"
        })

    # =========================================================
    # 2) الفرع
    # =========================================================
    branch=first("branches")
    if not branch:
        branch=ins("branches",{
            "company_id":company,
            "name":"الفرع الرئيسي",
            "code":"BR-001",
            "phone":"0500000000",
            "address":"حي الصفا، شارع عبدالله بن سهل، جدة"
        })

    # =========================================================
    # 3) المستودع
    # =========================================================
    warehouse=first("warehouses")
    if not warehouse:
        warehouse=ins("warehouses",{
            "branch_id":branch,
            "name":"المستودع الرئيسي",
            "code":"WH-001"
        })

    # =========================================================
    # 4) التصنيفات
    # =========================================================
    categories={}
    for name in ["أقلام","دفاتر","أدوات مدرسية","أدوات فنية","طباعة","إكسسوارات تقنية"]:
        r=cur.execute("SELECT id FROM product_categories WHERE name_ar=?",(name,)).fetchone() if exists("product_categories") and "name_ar" in cols("product_categories") else None
        categories[name]=r[0] if r else ins("product_categories",{"name_ar":name,"name":name,"is_active":1})

    # =========================================================
    # 5) العلامات
    # =========================================================
    brands={}
    for name in ["Pilot","BIC","Faber-Castell","Staedtler","Oxford"]:
        r=cur.execute("SELECT id FROM brands WHERE name=?",(name,)).fetchone() if exists("brands") and "name" in cols("brands") else None
        brands[name]=r[0] if r else ins("brands",{"name":name,"is_active":1})

    # =========================================================
    # 6) الوحدات
    # =========================================================
    units={}
    for name in ["حبة","علبة","دفتر","رزمة","خدمة"]:
        r=cur.execute("SELECT id FROM units WHERE name=?",(name,)).fetchone() if exists("units") and "name" in cols("units") else None
        units[name]=r[0] if r else ins("units",{"name":name,"is_active":1})

    # =========================================================
    # 7) الضرائب
    # =========================================================
    tax=cur.execute("SELECT id FROM tax_rates ORDER BY id LIMIT 1").fetchone() if exists("tax_rates") else None
    tax_id=tax[0] if tax else ins("tax_rates",{"code":"VAT15","name":"ضريبة القيمة المضافة","rate":15,"is_active":1})

    # =========================================================
    # 8) الحسابات
    # =========================================================
    accounts=[
        ("1100","الخزينة","asset"),
        ("1200","البنوك","asset"),
        ("1300","العملاء","asset"),
        ("1400","المخزون","asset"),
        ("1410","ضريبة القيمة المضافة - مدخلات","asset"),
        ("2100","الموردون","liability"),
        ("2200","ضريبة القيمة المضافة - مخرجات","liability"),
        ("4100","مبيعات القرطاسية","revenue"),
        ("4200","خدمات الطباعة","revenue"),
        ("5100","تكلفة البضاعة المباعة","expense")
    ]
    amap={}
    for code,name,typ in accounts:
        r=cur.execute("SELECT id FROM accounts WHERE account_code=?",(code,)).fetchone()
        if not r:
            aid=ins("accounts",{
                "account_code":code,
                "account_name":name,
                "account_type":typ,
                "is_active":1,
                "allow_posting":1,
                "opening_balance":0
            })
        else: aid=r[0]
        amap[code]=aid

    # =========================================================
    # 9) المستخدم
    # =========================================================
    user=first("users")
    if not user:
        user=ins("users",{
            "username":"admin",
            "full_name":"مدير النظام",
            "is_active":1
        })

    # =========================================================
    # 10) الموردون
    # =========================================================
    suppliers=[]
    supplier_data=[
        ("SUP-001","مؤسسة النور للقرطاسية","0501111111"),
        ("SUP-002","شركة الإمداد المدرسي","0502222222"),
        ("SUP-003","مؤسسة التقنية الحديثة","0503333333")
    ]
    for code,name,phone in supplier_data:
        r=cur.execute("SELECT id FROM suppliers WHERE supplier_code=?",(code,)).fetchone() if "code" in cols("suppliers") else None
        sid=r[0] if r else ins("suppliers",{
            "supplier_code":code,"name":name,"phone":phone,
            "is_active":1
        })
        suppliers.append(sid)

    # =========================================================
    # 11) العملاء
    # =========================================================
    customers=[]
    customer_data=[
        ("CUS-001","أحمد محمد","0504444441"),
        ("CUS-002","مدرسة اليقظة","0504444442"),
        ("CUS-003","مؤسسة التعليم الحديث","0504444443"),
        ("CUS-004","محمد علي","0504444444")
    ]
    for code,name,phone in customer_data:
        r=cur.execute("SELECT id FROM customers WHERE customer_code=?",(code,)).fetchone() if "code" in cols("customers") else None
        cid=r[0] if r else ins("customers",{
            "supplier_code":code,"name":name,"phone":phone,
            "is_active":1
        })
        customers.append(cid)

    # =========================================================
    # 12) المنتجات
    # =========================================================
    products=[]
    pdata=[
        ("SKU-001","قلم حبر أزرق","Pilot",1.50,3.00,"أقلام","حبة"),
        ("SKU-002","قلم رصاص HB","Faber-Castell",1.00,2.00,"أقلام","حبة"),
        ("SKU-003","دفتر 100 ورقة","Oxford",6.00,10.00,"دفاتر","دفتر"),
        ("SKU-004","دفتر 200 ورقة","Oxford",10.00,16.00,"دفاتر","دفتر"),
        ("SKU-005","ألوان خشبية 12 لون","Faber-Castell",8.00,14.00,"أدوات فنية","علبة"),
        ("SKU-006","مسطرة 30 سم","Staedtler",1.50,3.00,"أدوات مدرسية","حبة"),
        ("SKU-007","ممحاة","BIC",0.75,1.50,"أدوات مدرسية","حبة"),
        ("SKU-008","مبراة","BIC",1.00,2.50,"أدوات مدرسية","حبة"),
        ("SKU-009","ورق A4","Oxford",12.00,18.00,"طباعة","رزمة"),
        ("SKU-010","خدمة طباعة أبيض وأسود","",0.20,0.50,"طباعة","خدمة")
    ]
    for sku,name,brand,cost,sale,cat,unit in pdata:
        r=cur.execute("SELECT id FROM products WHERE sku=?",(sku,)).fetchone()
        if r:
            pid=r[0]
        else:
            pid=ins("products",{
                "sku":sku,
                "name_ar":name,
                "name":name,
                "category_id":categories.get(cat),
                "brand_id":brands.get(brand) if brand else None,
                "unit_id":units.get(unit),
                "product_type":"SERVICE" if unit=="خدمة" else "PRODUCT",
                "cost_price":cost,
                "sale_price":sale,
                "wholesale_price":round(sale*.9,2),
                "school_price":round(sale*.85,2),
                "corporate_price":round(sale*.85,2),
                "min_price":cost,
                "reorder_point":5,
                "min_stock":3,
                "max_stock":100,
                "is_active":1,
                "created_at":now,
                "updated_at":now
            })
        products.append((pid,cost,sale))

    # =========================================================
    # 13) المخزون الافتتاحي
    # =========================================================
    for pid,cost,sale in products:
        if exists("stock_movements"):
            already=cur.execute(
                "SELECT COUNT(*) FROM stock_movements WHERE product_id=? AND movement_type='OPENING'",
                (pid,)
            ).fetchone()[0]
            if not already:
                qty=100 if pid != products[-1][0] else 0
                if qty:
                    ins("stock_movements",{
                        "product_id":pid,
                        "warehouse_id":warehouse,
                        "movement_type":"OPENING",
                        "quantity":qty,
                        "unit_cost":cost,
                        "reference_type":"OPENING",
                        "reference_id":None,
                        "notes":"رصيد افتتاحي",
                        "created_at":now
                    })

    # =========================================================
    # 14) شراء حقيقي
    # =========================================================
    po_id=None
    if exists("purchase_orders"):
        po_no=f"PO-{datetime.datetime.now().year}-000001"
        if cur.execute("SELECT 1 FROM purchase_orders WHERE order_number=?",(po_no,)).fetchone():
            po_id=cur.execute("SELECT id FROM purchase_orders WHERE order_number=?",(po_no,)).fetchone()[0]
        else:
            items=[
                (products[0][0],50,products[0][1]),
                (products[1][0],50,products[1][1]),
                (products[2][0],30,products[2][1]),
                (products[8][0],20,products[8][1])
            ]
            subtotal=sum(q*c for _,q,c in items)
            vat=round(subtotal*.15,2)
            total=round(subtotal+vat,2)
            po_id=ins("purchase_orders",{
                "order_number":po_no,
                "branch_id":branch,
                "supplier_id":suppliers[0],
                "status":"RECEIVED",
                "subtotal":subtotal,
                "discount_amount":0,
                "tax_amount":vat,
                "total_amount":total,
                "notes":"أمر شراء تجريبي مترابط",
                "created_at":now
            })
            for pid,q,cost in items:
                ins("purchase_order_items",{
                    "order_id":po_id,
                    "purchase_order_id":po_id,
                    "product_id":pid,
                    "quantity":q,
                    "unit_cost":cost,
                    "tax_amount":round(q*cost*.15,2),
                    "line_total":round(q*cost*1.15,2)
                })

            # فاتورة المورد
            if exists("purchase_invoices"):
                invno=f"PINV-{datetime.datetime.now().year}-000001"
                pinv=ins("purchase_invoices",{
                    "invoice_number":invno,
                    "supplier_id":suppliers[0],
                    "purchase_order_id":po_id,
                    "subtotal":subtotal,
                    "tax_amount":vat,
                    "total_amount":total,
                    "paid_amount":0,
                    "due_amount":total,
                    "status":"POSTED",
                    "invoice_date":now[:10],
                    "due_date":(datetime.date.today()+datetime.timedelta(days=30)).isoformat()
                })
                if exists("purchase_invoice_items"):
                    for pid,q,cost in items:
                        ins("purchase_invoice_items",{
                            "invoice_id":pinv,
                            "purchase_invoice_id":pinv,
                            "product_id":pid,
                            "quantity":q,
                            "unit_cost":cost,
                            "tax_amount":round(q*cost*.15,2),
                            "line_total":round(q*cost*1.15,2)
                        })

            # استلام المخزون
            for pid,q,cost in items:
                ins("stock_movements",{
                    "product_id":pid,
                    "warehouse_id":warehouse,
                    "movement_type":"PURCHASE",
                    "quantity":q,
                    "unit_cost":cost,
                    "reference_type":"PURCHASE_ORDER",
                    "reference_id":po_id,
                    "notes":"استلام مشتريات",
                    "created_at":now
                })

    # =========================================================
    # 15) مبيعات فعلية متعددة
    # =========================================================
    sales_created=[]
    for n,cid in enumerate(customers[:4],1):
        sale_no=f"INV-{datetime.datetime.now().year}-{n:06d}"
        if cur.execute("SELECT id FROM sales WHERE invoice_number=?",(sale_no,)).fetchone():
            continue

        items=[
            (products[(n-1)%8][0],2,products[(n-1)%8][2],products[(n-1)%8][1]),
            (products[(n)%8][0],1,products[(n)%8][2],products[(n)%8][1])
        ]
        subtotal=sum(q*p for _,q,p,_ in items)
        vat=round(subtotal*.15,2)
        total=round(subtotal+vat,2)

        sid=ins("sales",{
            "invoice_number":sale_no,
            "branch_id":branch,
            "warehouse_id":warehouse,
            "customer_id":cid,
            "cashier_id":user,
            "status":"POSTED",
            "subtotal":subtotal,
            "discount_amount":0,
            "tax_amount":vat,
            "total_amount":total,
            "paid_amount":total,
            "due_amount":0,
            "notes":"فاتورة بيع تشغيلية",
            "created_at":now
        })

        for pid,q,price,cost in items:
            ins("sale_items",{
                "sale_id":sid,
                "product_id":pid,
                "quantity":q,
                "unit_price":price,
                "discount_amount":0,
                "tax_amount":round(q*price*.15,2),
                "line_total":round(q*price*1.15,2)
            })
            ins("stock_movements",{
                "product_id":pid,
                "warehouse_id":warehouse,
                "movement_type":"SALE",
                "quantity":-q,
                "unit_cost":cost,
                "reference_type":"SALE",
                "reference_id":sid,
                "notes":"صرف بسبب البيع",
                "created_at":now
            })

        ins("sale_payments",{
            "sale_id":sid,
            "payment_method":"CASH",
            "amount":total,
            "reference_number":f"CASH-{sid}",
            "notes":"دفع نقدي"
        })

        # قيد البيع
        if exists("journal_entries"):
            en=f"JE-SALE-{sid:06d}"
            jid=ins("journal_entries",{
                "entry_number":en,
                "entry_date":now[:10],
                "description":f"قيد فاتورة بيع {sale_no}",
                "source_type":"SALE",
                "source_id":sid,
                "status":"POSTED",
                "created_by":user,
                "created_at":now
            })
            cost=sum(q*c for _,q,_,c in items)
            lines=[
                (amap["1100"],total,0),
                (amap["4100"],0,subtotal),
                (amap["2200"],0,vat),
                (amap["5100"],cost,0),
                (amap["1400"],0,cost)
            ]
            for aid,debit,credit in lines:
                ins("journal_entry_lines",{
                    "journal_entry_id":jid,
                    "account_id":aid,
                    "description":f"فاتورة بيع {sale_no}",
                    "debit":debit,
                    "credit":credit
                })
        sales_created.append(sid)

    # =========================================================
    # 16) حركة خزينة
    # =========================================================
    if exists("cash_transactions"):
        total_cash=cur.execute(
            "SELECT COALESCE(SUM(amount),0) FROM sale_payments WHERE payment_method='CASH'"
        ).fetchone()[0]
        if total_cash:
            if not cur.execute(
                "SELECT 1 FROM cash_transactions WHERE reference_type='SALES_SEED'"
            ).fetchone() if "reference_type" in cols("cash_transactions") else True:
                ins("cash_transactions",{
                    "transaction_type":"SALE",
                    "amount":total_cash,
                    "reference_type":"SALES_SEED",
                    "reference_id":None,
                    "description":"إجمالي المقبوضات النقدية التجريبية",
                    "created_at":now
                })

    # =========================================================
    # 17) تحديث حالة الإعدادات
    # =========================================================
    if exists("system_settings"):
        for key,val in [
            ("erp_demo_data_loaded","true"),
            ("erp_data_seed_date",now),
            ("erp_seed_version","1.0.0"),
            ("offline_first","true")
        ]:
            if cur.execute("SELECT 1 FROM system_settings WHERE setting_key=?",(key,)).fetchone():
                cur.execute("UPDATE system_settings SET setting_value=?,updated_at=? WHERE setting_key=?",(val,now,key))
            else:
                ins("system_settings",{
                    "setting_key":key,
                    "setting_value":val,
                    "value_type":"string",
                    "description":"إعداد أنشأه التهيئة التشغيلية"
                })

    con.commit()

    # =========================================================
    # 18) الفحص النهائي
    # =========================================================
    fk=cur.execute("PRAGMA foreign_key_check").fetchall()
    integrity=cur.execute("PRAGMA integrity_check").fetchone()[0]

    print("="*70)
    print("COMPLETE ERP OPERATIONAL SEED")
    print("="*70)
    print("BACKUP:",backup)
    print("COMPANY:",company)
    print("BRANCH:",branch)
    print("WAREHOUSE:",warehouse)
    print("PRODUCTS:",cur.execute("SELECT COUNT(*) FROM products").fetchone()[0])
    print("CUSTOMERS:",cur.execute("SELECT COUNT(*) FROM customers").fetchone()[0])
    print("SUPPLIERS:",cur.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0])
    print("PURCHASE ORDERS:",cur.execute("SELECT COUNT(*) FROM purchase_orders").fetchone()[0])
    print("PURCHASE INVOICES:",cur.execute("SELECT COUNT(*) FROM purchase_invoices").fetchone()[0])
    print("SALES:",cur.execute("SELECT COUNT(*) FROM sales").fetchone()[0])
    print("SALE ITEMS:",cur.execute("SELECT COUNT(*) FROM sale_items").fetchone()[0])
    print("STOCK MOVEMENTS:",cur.execute("SELECT COUNT(*) FROM stock_movements").fetchone()[0])
    print("JOURNAL ENTRIES:",cur.execute("SELECT COUNT(*) FROM journal_entries").fetchone()[0])
    print("JOURNAL LINES:",cur.execute("SELECT COUNT(*) FROM journal_entry_lines").fetchone()[0])
    print("INTEGRITY:",integrity)
    print("FOREIGN KEY ERRORS:",len(fk))
    print("="*70)

    if integrity=="ok" and len(fk)==0:
        print("STATUS: SUCCESS")
    else:
        print("STATUS: FAILED")

except Exception as e:
    con.rollback()
    print("="*70)
    print("STATUS: FAILED")
    print(type(e).__name__+":"+str(e))
    print("BACKUP AVAILABLE:",backup)
finally:
    con.close()


