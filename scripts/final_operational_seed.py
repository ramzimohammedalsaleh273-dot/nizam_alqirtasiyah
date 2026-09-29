import os,sqlite3,shutil,datetime,traceback
from app.services.erp_engine import ERP

BASE=os.getcwd()
DB=os.path.join(BASE,"database","nizam_alqirtasiyah.db")
BACK=os.path.join(BASE,"backups")
os.makedirs(BACK,exist_ok=True)
stamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup=os.path.join(BACK,f"before_final_operational_seed_{stamp}.db")

print("="*78)
print("FINAL OPERATIONAL TRANSACTION SEED")
print("="*78)

shutil.copy2(DB,backup)
print("BACKUP:",backup)

con=sqlite3.connect(DB)
con.execute("PRAGMA foreign_keys=ON")
con.execute("PRAGMA busy_timeout=10000")

try:
    branch=con.execute("SELECT id FROM branches ORDER BY id LIMIT 1").fetchone()[0]
    warehouse=con.execute("SELECT id FROM warehouses ORDER BY id LIMIT 1").fetchone()[0]
    user=con.execute("SELECT id FROM users ORDER BY id LIMIT 1").fetchone()[0]
    supplier=con.execute("SELECT id FROM suppliers ORDER BY id LIMIT 1").fetchone()[0]
    customer=con.execute("SELECT id FROM customers ORDER BY id LIMIT 1").fetchone()[0]

    products=con.execute("""
        SELECT id,cost_price,sale_price
        FROM products
        WHERE is_active=1
        ORDER BY id
        LIMIT 5
    """).fetchall()

    if not products:
        raise RuntimeError("NO ACTIVE PRODUCTS")

    erp=ERP(DB)

    # --------------------------------------------------
    # PURCHASE
    # --------------------------------------------------
    print("\n[1] PURCHASE")

    p=products[0]
    cost=float(p[1] or 10)

    purchase=erp.create_purchase(
        supplier,
        [
            {
                "product_id":p[0],
                "quantity":20,
                "unit_cost":cost
            }
        ]
    )

    print("PURCHASE:",purchase)

    received=erp.receive_purchase(
        supplier,
        warehouse,
        [
            {
                "product_id":p[0],
                "quantity":20,
                "unit_cost":cost
            }
        ],
        branch_id=branch,
        tax_rate=15
    )

    print("RECEIVED:",received)

    # --------------------------------------------------
    # SALE 1
    # --------------------------------------------------
    print("\n[2] SALE 1")

    price=float(p[2] or 15)
    total=round(price*2*1.15,2)

    sale1=erp.create_sale(
        warehouse,
        [
            {
                "product_id":p[0],
                "quantity":2,
                "unit_price":price
            }
        ],
        customer_id=None,
        branch_id=branch,
        cashier_id=user,
        payments=[
            {
                "payment_method":"CASH",
                "amount":total
            }
        ],
        tax_rate=15
    )

    print("SALE 1:",sale1)

    # --------------------------------------------------
    # SALE 2
    # --------------------------------------------------
    if False:
        p2=products[1]
        price2=float(p2[2] or 15)
        total2=round(price2*1.15,2)

        print("\n[3] SALE 2")

        sale2=erp.create_sale(
            warehouse,
            [
                {
                    "product_id":p2[0],
                    "quantity":1,
                    "unit_price":price2
                }
            ],
            customer_id=customer,
            branch_id=branch,
            cashier_id=user,
            payments=[
                {
                    "payment_method":"CASH",
                    "amount":total2
                }
            ],
            tax_rate=15
        )

        print("SALE 2:",sale2)

    # --------------------------------------------------
    # VALIDATION
    # --------------------------------------------------
    print("\n[4] VALIDATION")

    tables=[
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
        exists=con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (t,)
        ).fetchone()

        if exists:
            n=con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
            print(f"{t:28} {n}")

    # قيود غير متوازنة
    bad=con.execute("""
        SELECT j.entry_number
        FROM journal_entries j
        JOIN journal_entry_lines l
          ON l.journal_entry_id=j.id
        GROUP BY j.id
        HAVING ROUND(SUM(l.debit),2)<>ROUND(SUM(l.credit),2)
    """).fetchall()

    integrity=con.execute("PRAGMA integrity_check").fetchone()[0]
    fk=con.execute("PRAGMA foreign_key_check").fetchall()

    print("\nUNBALANCED JOURNALS:",len(bad))
    print("INTEGRITY:",integrity)
    print("FOREIGN KEY ERRORS:",len(fk))

    if bad:
        raise RuntimeError("UNBALANCED JOURNALS")

    if integrity!="ok":
        raise RuntimeError("DATABASE INTEGRITY FAILED")

    if fk:
        raise RuntimeError("FOREIGN KEY ERRORS")

    con.commit()

    print("\n"+"="*78)
    print("STATUS: SUCCESS")
    print("PURCHASE + RECEIVING + SALES + STOCK + ACCOUNTING")
    print("ALL BASIC LINK CHECKS PASSED")
    print("BACKUP:",backup)
    print("="*78)

except Exception as e:
    con.rollback()
    print("\n"+"="*78)
    print("STATUS: FAILED")
    print(type(e).__name__+":"+str(e))
    print("DATABASE WAS ROLLED BACK")
    print("BACKUP:",backup)
    print("="*78)
    traceback.print_exc()

finally:
    con.close()

