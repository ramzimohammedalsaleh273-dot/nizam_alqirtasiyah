import os, shutil, sqlite3, datetime, traceback, sys

BASE=os.getcwd()
DB=os.path.join(BASE,"database","nizam_alqirtasiyah.db")
BACK=os.path.join(BASE,"backups")
os.makedirs(BACK,exist_ok=True)

stamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup=os.path.join(BACK,f"before_real_transactions_{stamp}.db")

print("="*78)
print("REAL ERP TRANSACTIONS - PURCHASE + SALES + ACCOUNTING")
print("="*78)

if not os.path.exists(DB):
    print("STATUS: FAILED")
    print("DATABASE NOT FOUND")
    raise SystemExit(1)

shutil.copy2(DB,backup)
print("BACKUP:",backup)

sys.path.insert(0,BASE)

from app.services.erp_engine import ERP, ERPError

def count(con,t):
    r=con.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
        (t,)
    ).fetchone()
    if not r or not r[0]:
        return None
    return con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]

con=sqlite3.connect(DB)
con.execute("PRAGMA foreign_keys=ON")
con.execute("PRAGMA busy_timeout=10000")

try:
    # ------------------------------------------------------------
    # 1) قراءة البيانات الأساسية الحالية
    # ------------------------------------------------------------
    company=con.execute(
        "SELECT id FROM companies ORDER BY id LIMIT 1"
    ).fetchone()
    branch=con.execute(
        "SELECT id FROM branches ORDER BY id LIMIT 1"
    ).fetchone()
    warehouse=con.execute(
        "SELECT id FROM warehouses ORDER BY id LIMIT 1"
    ).fetchone()
    user=con.execute(
        "SELECT id FROM users ORDER BY id LIMIT 1"
    ).fetchone()
    supplier=con.execute(
        "SELECT id FROM suppliers ORDER BY id LIMIT 1"
    ).fetchone()
    customer=con.execute(
        "SELECT id FROM customers ORDER BY id LIMIT 1"
    ).fetchone()

    products=con.execute(
        "SELECT id,sku,name_ar,cost_price,sale_price "
        "FROM products WHERE is_active=1 ORDER BY id LIMIT 5"
    ).fetchall()

    if not branch or not warehouse or not user or not supplier or not products:
        raise RuntimeError(
            "MASTER DATA INCOMPLETE: branch/warehouse/user/supplier/products"
        )

    branch_id=branch[0]
    warehouse_id=warehouse[0]
    user_id=user[0]
    supplier_id=supplier[0]
    customer_id=customer[0] if customer else None

    print("\nMASTER DATA: PASSED")
    print("BRANCH:",branch_id)
    print("WAREHOUSE:",warehouse_id)
    print("USER:",user_id)
    print("SUPPLIER:",supplier_id)
    print("CUSTOMER:",customer_id)
    print("PRODUCTS:",len(products))

    # ------------------------------------------------------------
    # 2) تشغيل محرك ERP على قاعدة البيانات الحالية
    # ------------------------------------------------------------
    erp=ERP(DB)

    # ------------------------------------------------------------
    # 3) إنشاء عملية شراء حقيقية
    # ------------------------------------------------------------
    p=products[0]
    product_id=p[0]
    cost=float(p[3] or 10)

    print("\n[1] PURCHASE")

    purchase=erp.create_purchase(
        supplier_id=supplier_id,
        branch_id=branch_id,
        warehouse_id=warehouse_id,
        items=[
            {
                "product_id":product_id,
                "quantity":20,
                "unit_cost":cost
            }
        ],
        tax_rate=15,
        notes="شراء تشغيلي تجريبي مترابط"
    )

    print("PURCHASE CREATED:",purchase)

    # استلام المشتريات
    received=erp.receive_purchase(purchase["purchase_order_id"])
    print("PURCHASE RECEIVED:",received)

    # ------------------------------------------------------------
    # 4) إنشاء مبيعات حقيقية متعددة
    # ------------------------------------------------------------
    print("\n[2] SALES")

    sale_results=[]

    sale1=erp.create_sale(
        branch_id=branch_id,
        warehouse_id=warehouse_id,
        customer_id=None,
        cashier_id=user_id,
        items=[
            {
                "product_id":product_id,
                "quantity":2,
                "unit_price":float(p[4] or 15)
            }
        ],
        payments=[
            {
                "payment_method":"CASH",
                "amount":round(2*float(p[4] or 15)*1.15,2)
            }
        ],
        tax_rate=15,
        notes="بيع نقدي تشغيلي"
    )
    sale_results.append(sale1)
    print("SALE 1:",sale1)

    # بيع ثانٍ لعميل مسجل إن وجد
    if customer_id and len(products)>1:
        p2=products[1]
        price2=float(p2[4] or 15)

        sale2=erp.create_sale(
            branch_id=branch_id,
            warehouse_id=warehouse_id,
            customer_id=customer_id,
            cashier_id=user_id,
            items=[
                {
                    "product_id":p2[0],
                    "quantity":1,
                    "unit_price":price2
                }
            ],
            payments=[
                {
                    "payment_method":"CASH",
                    "amount":round(price2*1.15,2)
                }
            ],
            tax_rate=15,
            notes="بيع عميل مسجل تشغيلي"
        )
        sale_results.append(sale2)
        print("SALE 2:",sale2)

    # ------------------------------------------------------------
    # 5) التحقق من النتائج قبل الحفظ النهائي
    # ------------------------------------------------------------
    print("\n[3] TRANSACTION COUNTS")

    tables=[
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
    ]

    for t in tables:
        n=count(con,t)
        if n is not None:
            print(f"{t:28} {n}")

    # ------------------------------------------------------------
    # 6) فحص توازن القيود
    # ------------------------------------------------------------
    print("\n[4] JOURNAL BALANCE")

    bad_entries=con.execute("""
        SELECT j.id,j.entry_number,
               ROUND(COALESCE(SUM(l.debit),0),2) debit_total,
               ROUND(COALESCE(SUM(l.credit),0),2) credit_total
        FROM journal_entries j
        LEFT JOIN journal_entry_lines l
          ON l.journal_entry_id=j.id
        GROUP BY j.id,j.entry_number
        HAVING ROUND(COALESCE(SUM(l.debit),0),2)
            <> ROUND(COALESCE(SUM(l.credit),0),2)
    """).fetchall()

    print("UNBALANCED ENTRIES:",len(bad_entries))

    if bad_entries:
        for row in bad_entries[:20]:
            print(row)
        raise RuntimeError("UNBALANCED JOURNAL ENTRIES")

    # ------------------------------------------------------------
    # 7) فحص حركة المخزون
    # ------------------------------------------------------------
    print("\n[5] STOCK MOVEMENTS")

    stock_rows=con.execute("""
        SELECT movement_type,
               COUNT(*),
               ROUND(COALESCE(SUM(quantity),0),3)
        FROM stock_movements
        GROUP BY movement_type
        ORDER BY movement_type
    """).fetchall()

    for row in stock_rows:
        print(row)

    # ------------------------------------------------------------
    # 8) فحص المبيعات الإجمالية
    # ------------------------------------------------------------
    sales_total=con.execute("""
        SELECT
          ROUND(COALESCE(SUM(subtotal),0),2),
          ROUND(COALESCE(SUM(tax_amount),0),2),
          ROUND(COALESCE(SUM(total_amount),0),2),
          ROUND(COALESCE(SUM(paid_amount),0),2),
          ROUND(COALESCE(SUM(due_amount),0),2)
        FROM sales
    """).fetchone()

    print("\nSALES TOTALS:",sales_total)

    # ------------------------------------------------------------
    # 9) فحص المشتريات الإجمالية
    # ------------------------------------------------------------
    purchase_total=con.execute("""
        SELECT
          ROUND(COALESCE(SUM(subtotal),0),2),
          ROUND(COALESCE(SUM(tax_amount),0),2),
          ROUND(COALESCE(SUM(total_amount),0),2),
          ROUND(COALESCE(SUM(paid_amount),0),2),
          ROUND(COALESCE(SUM(due_amount),0),2)
        FROM purchase_invoices
    """).fetchone()

    print("PURCHASE TOTALS:",purchase_total)

    # ------------------------------------------------------------
    # 10) SQLite + FK
    # ------------------------------------------------------------
    integrity=con.execute(
        "PRAGMA integrity_check"
    ).fetchone()[0]

    fk=con.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    print("\n[6] DATABASE")
    print("INTEGRITY:",integrity)
    print("FOREIGN KEY ERRORS:",len(fk))

    if integrity!="ok":
        raise RuntimeError("DATABASE INTEGRITY FAILED")

    if fk:
        for row in fk[:20]:
            print(row)
        raise RuntimeError("FOREIGN KEY ERRORS FOUND")

    con.commit()

    print("\n"+"="*78)
    print("REAL TRANSACTIONS: SUCCESS")
    print("PURCHASE + RECEIVING + SALES + STOCK + VAT + ACCOUNTING CREATED")
    print("UNBALANCED JOURNALS:",len(bad_entries))
    print("FOREIGN KEY ERRORS:",len(fk))
    print("BACKUP:",backup)
    print("STATUS: SUCCESS")
    print("="*78)

except Exception as e:
    con.rollback()
    print("\n"+"="*78)
    print("STATUS: FAILED")
    print(type(e).__name__+":"+str(e))
    print("DATABASE WAS ROLLED BACK")
    print("BACKUP AVAILABLE:",backup)
    print("="*78)
    traceback.print_exc()

finally:
    try:
        con.close()
    except:
        pass
