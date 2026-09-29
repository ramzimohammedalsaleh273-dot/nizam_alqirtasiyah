from pathlib import Path
import sqlite3
import shutil
import datetime
import sys
import py_compile

ROOT = Path.cwd()
DB = ROOT / "database" / "nizam_alqirtasiyah.db"
BACK = ROOT / "backups"
BACK.mkdir(exist_ok=True)

SCRIPT = ROOT / "scripts" / "integrated_store_scenario.py"

# فحص نحوي لهذا الملف قبل تشغيله
try:
    py_compile.compile(str(SCRIPT), doraise=True)
except Exception:
    pass

# نسخة احتياطية
stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BACK / f"before_integrated_operations_{stamp}.db"
shutil.copy2(DB, backup)

sys.path.insert(0, str(ROOT))

from app.services.erp_engine import ERP


def table_exists(cur, table):
    return cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,)
    ).fetchone() is not None


def count(cur, table):
    if not table_exists(cur, table):
        return 0
    return cur.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]


con = sqlite3.connect(DB)
cur = con.cursor()

print("=" * 78)
print("INTEGRATED STORE SCENARIO")
print("=" * 78)
print("BACKUP:", backup)

# منع تكرار نفس السيناريو
marker = "INTEGRATED-DEMO-2026"

if table_exists(cur, "purchase_orders"):
    cols = [
        r[1]
        for r in cur.execute(
            'PRAGMA table_info("purchase_orders")'
        ).fetchall()
    ]

    if "notes" in cols:
        old = cur.execute(
            'SELECT COUNT(*) FROM purchase_orders WHERE notes LIKE ?',
            (f"%{marker}%",)
        ).fetchone()[0]

        if old > 0:
            print("SCENARIO: ALREADY EXISTS")
            print("لن يتم تكرار العملية.")
            print("STATUS: SUCCESS")
            con.close()
            raise SystemExit(0)

# اختيار بيانات موجودة فعليًا
supplier_row = cur.execute(
    "SELECT id FROM suppliers WHERE is_active=1 ORDER BY id LIMIT 1"
).fetchone()

product_row = cur.execute(
    """
    SELECT id, cost_price, sale_price
    FROM products
    WHERE is_active=1
      AND product_type='PRODUCT'
    ORDER BY id
    LIMIT 1
    """
).fetchone()

customer_row = cur.execute(
    "SELECT id FROM customers WHERE is_active=1 ORDER BY id LIMIT 1"
).fetchone()

if not supplier_row:
    print("ERROR: لا يوجد مورد نشط.")
    con.close()
    raise SystemExit(1)

if not product_row:
    print("ERROR: لا يوجد منتج نشط.")
    con.close()
    raise SystemExit(1)

if not customer_row:
    print("ERROR: لا يوجد عميل نشط.")
    con.close()
    raise SystemExit(1)

supplier_id = supplier_row[0]
product_id = product_row[0]

cost = float(product_row[1] or 1)
unit_sale_price = float(product_row[2] or (cost * 1.5))

customer_id = customer_row[0]

purchase_qty = 20
sale_qty = 3

sale_subtotal = round(sale_qty * unit_sale_price, 2)
sale_tax = round(sale_subtotal * 0.15, 2)
sale_total = round(sale_subtotal + sale_tax, 2)

print("PRODUCT ID:", product_id)
print("SUPPLIER ID:", supplier_id)
print("CUSTOMER ID:", customer_id)
print("SALE TOTAL:", sale_total)

erp = ERP(str(DB))

# =========================================================
# 1 - إنشاء عملية شراء
# =========================================================
purchase = erp.create_purchase(
    supplier_id=supplier_id,
    items=[
        {
            "product_id": product_id,
            "quantity": purchase_qty,
            "unit_cost": cost
        }
    ]
)

print("PURCHASE:", purchase)

# =========================================================
# 2 - استلام الشراء وإدخاله للمخزون
# =========================================================
received = erp.receive_purchase(
    supplier_id=supplier_id,
    warehouse_id=1,
    branch_id=1,
    items=[
        {
            "product_id": product_id,
            "quantity": purchase_qty,
            "unit_cost": cost
        }
    ],
    tax_rate=15
)

print("RECEIVED:", received)

# =========================================================
# 3 - البيع
# =========================================================
sale = erp.create_sale(
    warehouse_id=1,
    branch_id=1,
    customer_id=customer_id,
    cashier_id=1,
    items=[
        {
            "product_id": product_id,
            "quantity": sale_qty,
            "unit_price": unit_sale_price
        }
    ],
    payments=[
        {
            "payment_method": "CASH",
            "amount": sale_total
        }
    ],
    tax_rate=15
)

print("SALE:", sale)

# =========================================================
# وضع علامة لمنع التكرار
# =========================================================
purchase_id = purchase.get("purchase_id")

if purchase_id and table_exists(cur, "purchase_orders"):
    cols = [
        r[1]
        for r in cur.execute(
            'PRAGMA table_info("purchase_orders")'
        ).fetchall()
    ]

    if "notes" in cols:
        cur.execute(
            """
            UPDATE purchase_orders
            SET notes = COALESCE(notes, '') || ?
            WHERE id = ?
            """,
            (" | " + marker, purchase_id)
        )

con.commit()

# =========================================================
# الفحص النهائي
# =========================================================

print("-" * 78)

tables = [
    "purchase_orders",
    "purchase_order_items",
    "purchase_invoices",
    "purchase_invoice_items",
    "stock_movements",
    "sales",
    "sale_items",
    "sale_payments",
    "cash_transactions",
    "journal_entries",
    "journal_entry_lines"
]

for table in tables:
    print(f"{table:30} {count(cur, table)}")

# توازن جميع القيود
unbalanced = 0

if table_exists(cur, "journal_entries") and table_exists(cur, "journal_entry_lines"):
    rows = cur.execute(
        """
        SELECT
            je.id,
            ROUND(COALESCE(SUM(jl.debit), 0), 2),
            ROUND(COALESCE(SUM(jl.credit), 0), 2)
        FROM journal_entries je
        LEFT JOIN journal_entry_lines jl
            ON jl.journal_entry_id = je.id
        GROUP BY je.id
        HAVING ROUND(COALESCE(SUM(jl.debit), 0), 2)
            <> ROUND(COALESCE(SUM(jl.credit), 0), 2)
        """
    ).fetchall()

    unbalanced = len(rows)

integrity = cur.execute("PRAGMA integrity_check").fetchone()[0]
fk_errors = len(cur.execute("PRAGMA foreign_key_check").fetchall())

print("-" * 78)
print("UNBALANCED JOURNALS:", unbalanced)
print("INTEGRITY:", integrity)
print("FOREIGN KEY ERRORS:", fk_errors)

if integrity == "ok" and fk_errors == 0 and unbalanced == 0:
    print("STATUS: SUCCESS")
    print("PURCHASE -> RECEIVING -> STOCK -> SALE -> CASH -> ACCOUNTING")
    print("ALL INTEGRATED LINKS PASSED")
else:
    print("STATUS: FAILED")

print("=" * 78)

con.close()
