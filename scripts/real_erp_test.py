from pathlib import Path
import sqlite3, shutil, sys, traceback

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/"database"/"nizam_alqirtasiyah.db"
TEST=ROOT/"database"/"_erp_test_copy.db"
con=None

try:
    if TEST.exists(): TEST.unlink()
    shutil.copy2(DB,TEST)
    print("TEST COPY: SUCCESS")

    con=sqlite3.connect(TEST)
    cur=con.cursor()

    supplier=cur.execute("SELECT id FROM suppliers LIMIT 1").fetchone()
    product=cur.execute("SELECT id FROM products LIMIT 1").fetchone()
    warehouse=cur.execute("SELECT id FROM warehouses LIMIT 1").fetchone()

    if not supplier or not product or not warehouse:
        raise RuntimeError("بيانات الاختبار الأساسية غير موجودة")

    con.close()
    con=None

    sys.path.insert(0,str(ROOT))
    from app.services.erp_engine import ERP
    erp=ERP(str(TEST))

    print("[1] HEALTH")
    print(erp.health_check())

    print("[2] PURCHASE")
    purchase=erp.create_purchase(
        supplier_id=supplier[0],
        items=[{"product_id":product[0],"quantity":5,"unit_cost":10}]
    )
    print(purchase)

    print("[3] RECEIVE")
    received=erp.receive_purchase(
        purchase["purchase_id"],
        warehouse[0],
        [{"product_id":product[0],"quantity":5,"unit_cost":10}]
    )
    print(received)

    print("[4] SALE")
    sale=erp.create_sale(
        warehouse_id=warehouse[0], customer_id=None, items=[{"product_id":product[0],"quantity":2,"unit_price":23}], payments=[{"payment_method":"CASH","amount":52.9}]
    )
    print(sale)

    con=sqlite3.connect(TEST)

    print("[5] LINK COUNTS")
    for table in [
        "purchase_orders",
        "purchase_order_items",
        "purchase_invoices",
        "purchase_invoice_items",
        "stock_movements",
        "sales",
        "sale_items",
        "sale_payments",
        "journal_entries",
        "journal_entry_lines"
    ]:
        try:
            print(table,":",con.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0])
        except Exception as e:
            print(table,": ERROR",e)

    print("="*60)
    print("STATUS: SUCCESS")
    print("="*60)

except Exception as e:
    print("="*60)
    print("STATUS: FAILED")
    print(type(e).__name__,str(e))
    traceback.print_exc()
    print("="*60)

finally:
    try:
        if con: con.close()
    except: pass
    try:
        if TEST.exists():
            TEST.unlink()
            print("TEST COPY REMOVED: OK")
    except Exception as e:
        print("TEST COPY CLEANUP:",e)

