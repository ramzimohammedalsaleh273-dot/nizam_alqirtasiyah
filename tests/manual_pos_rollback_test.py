import sqlite3
from decimal import Decimal
from app.database.connection import get_session
from app.services.pos_service import POSService

DB = "database/nizam_alqirtasiyah.db"

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

before = {
    "sales": con.execute("SELECT COUNT(*) FROM sales").fetchone()[0],
    "sale_items": con.execute("SELECT COUNT(*) FROM sale_items").fetchone()[0],
    "payments": con.execute("SELECT COUNT(*) FROM sale_payments").fetchone()[0],
    "movements": con.execute("SELECT COUNT(*) FROM stock_movements").fetchone()[0],
    "journals": con.execute("SELECT COUNT(*) FROM journal_entries").fetchone()[0],
    "journal_lines": con.execute("SELECT COUNT(*) FROM journal_entry_lines").fetchone()[0],
    "customer_transactions": con.execute(
        "SELECT COUNT(*) FROM customer_transactions"
    ).fetchone()[0],
}
con.close()

print()
print("الحالة قبل الاختبار:")
for k, v in before.items():
    print(f"  {k}: {v}")

# اختيار صنف متوفر
con = sqlite3.connect(DB)
product = con.execute("""
    SELECT
        p.id,
        p.name_ar,
        p.sale_price,
        s.available_quantity,
        s.average_cost
    FROM products p
    JOIN stock s
      ON s.product_id=p.id
     AND s.warehouse_id=1
    WHERE p.is_active=1
      AND s.available_quantity > 0
    ORDER BY p.id
    LIMIT 1
""").fetchone()
con.close()

if not product:
    raise RuntimeError("لا يوجد صنف متوفر لاختبار عملية البيع")

product_id, product_name, sale_price, available, average_cost = product

print()
print("الصنف المستخدم للاختبار:")
print("  ID:", product_id)
print("  الاسم:", product_name)
print("  السعر:", sale_price)
print("  المتاح:", available)
print("  التكلفة:", average_cost)

# نستخدم كمية 1 فقط
# الاختبار سيتم التراجع عنه بالكامل
try:
    with get_session() as session:
        result = POSService.create_sale(
            items=[
                {
                    "product_id": product_id,
                    "quantity": 1,
                    "unit_price": sale_price,
                    "discount": 0,
                }
            ],
            payment_method="cash",
            customer_id=None,
            warehouse_id=1,
            branch_id=1,
            cashier_id=None,
            reference_number="TEST-ROLLBACK",
            notes="اختبار تكامل آمن - سيتم التراجع عنه",
        )

        print()
        print("نتيجة إنشاء العملية:")
        print(result)

        # التراجع داخل نفس الاختبار
        session.rollback()

except Exception as e:
    print()
    print("حدث استثناء أثناء الاختبار:")
    print(type(e).__name__, str(e))
    raise

# التأكد أن كل شيء عاد كما كان
con = sqlite3.connect(DB)

after = {
    "sales": con.execute("SELECT COUNT(*) FROM sales").fetchone()[0],
    "sale_items": con.execute("SELECT COUNT(*) FROM sale_items").fetchone()[0],
    "payments": con.execute("SELECT COUNT(*) FROM sale_payments").fetchone()[0],
    "movements": con.execute("SELECT COUNT(*) FROM stock_movements").fetchone()[0],
    "journals": con.execute("SELECT COUNT(*) FROM journal_entries").fetchone()[0],
    "journal_lines": con.execute("SELECT COUNT(*) FROM journal_entry_lines").fetchone()[0],
    "customer_transactions": con.execute(
        "SELECT COUNT(*) FROM customer_transactions"
    ).fetchone()[0],
}

integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
foreign_keys = len(con.execute("PRAGMA foreign_key_check").fetchall())

con.close()

print()
print("الحالة بعد ROLLBACK:")
for k, v in after.items():
    print(f"  {k}: {v}")

print()
print("SQLite:", integrity)
print("Foreign Keys:", foreign_keys)

if before != after:
    raise AssertionError(
        "فشل الاختبار: تغيرت بيانات قاعدة البيانات رغم ROLLBACK"
    )

if integrity != "ok":
    raise AssertionError("فشل سلامة SQLite")

if foreign_keys != 0:
    raise AssertionError("وجدت أخطاء Foreign Keys")

print()
print("============================================================")
print("PASS: عملية البيع اختُبرت دون ترك أي بيانات جديدة.")
print("============================================================")
