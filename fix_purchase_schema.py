from pathlib import Path
import shutil,datetime,sqlite3

ROOT=Path.cwd()
DB=ROOT/"database"/"nizam_alqirtasiyah.db"
BACKUPS=ROOT/"database"/"backups"
BACKUPS.mkdir(parents=True,exist_ok=True)

stamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup=BACKUPS/f"nizam_alqirtasiyah_before_purchase_schema_fix_{stamp}.db"
shutil.copy2(DB,backup)

# ============================================================
# قراءة البنية الحقيقية لجدول المشتريات
# ============================================================
con=sqlite3.connect(DB)
cur=con.cursor()

columns=[
    row[1]
    for row in cur.execute(
        "PRAGMA table_info(purchase_invoices)"
    ).fetchall()
]

print("="*70)
print("فحص بنية جدول purchase_invoices")
print("="*70)
print("الأعمدة:",", ".join(columns))

# ============================================================
# اختيار عمود التاريخ الموجود فعلياً
# ============================================================
date_column=None

for candidate in [
    "invoice_date",
    "created_date",
    "date",
    "updated_at"
]:
    if candidate in columns:
        date_column=candidate
        break

# إذا لم يوجد أي عمود تاريخ، نستخدم id للترتيب فقط
order_column=date_column if date_column else "id"

# ============================================================
# إعادة بناء sales_service.py بالاعتماد على البنية الحقيقية
# ============================================================
sales_service=ROOT/"app/services/sales_service.py"

sales_service.write_text(
f'''from sqlalchemy import text
from app.database.connection import get_session


class SalesService:

    @staticmethod
    def list_sales(limit=100):
        with get_session() as s:
            rows=s.execute(text("""
                SELECT
                    id,
                    invoice_number,
                    customer_id,
                    subtotal,
                    discount_amount,
                    tax_amount,
                    total_amount,
                    paid_amount,
                    due_amount,
                    status,
                    created_at
                FROM sales
                ORDER BY id DESC
                LIMIT :limit
            """), {{"limit":limit}}).fetchall()

            return [dict(r._mapping) for r in rows]


    @staticmethod
    def get_sale(sale_id):
        with get_session() as s:
            sale=s.execute(text("""
                SELECT *
                FROM sales
                WHERE id=:id
            """), {{"id":sale_id}}).fetchone()

            if not sale:
                return None

            items=s.execute(text("""
                SELECT
                    si.*,
                    p.name_ar,
                    p.sku
                FROM sale_items si
                JOIN products p
                    ON p.id=si.product_id
                WHERE si.sale_id=:id
                ORDER BY si.id
            """), {{"id":sale_id}}).fetchall()

            result=dict(sale._mapping)
            result["items"]=[dict(x._mapping) for x in items]

            return result


class PurchaseService:

    @staticmethod
    def list_purchases(limit=100):
        with get_session() as s:
            rows=s.execute(text("""
                SELECT
                    pi.id,
                    pi.invoice_number,
                    pi.supplier_id,
                    pi.subtotal,
                    pi.tax_amount,
                    pi.total_amount,
                    pi.paid_amount,
                    pi.due_amount,
                    pi.status,
                    pi.{order_column} AS purchase_date
                FROM purchase_invoices pi
                ORDER BY pi.id DESC
                LIMIT :limit
            """), {{"limit":limit}}).fetchall()

            return [dict(r._mapping) for r in rows]


    @staticmethod
    def get_purchase(invoice_id):
        with get_session() as s:
            invoice=s.execute(text("""
                SELECT *
                FROM purchase_invoices
                WHERE id=:id
            """), {{"id":invoice_id}}).fetchone()

            if not invoice:
                return None

            item_columns=[
                row[1]
                for row in s.connection().exec_driver_sql(
                    "PRAGMA table_info(purchase_invoice_items)"
                ).fetchall()
            ]

            # تحديد اسم عمود ربط الفاتورة الحقيقي
            if "invoice_id" in item_columns:
                invoice_fk="invoice_id"
            elif "purchase_invoice_id" in item_columns:
                invoice_fk="purchase_invoice_id"
            else:
                invoice_fk=None

            if invoice_fk:
                items=s.execute(text(f"""
                    SELECT
                        pii.*,
                        p.name_ar,
                        p.sku
                    FROM purchase_invoice_items pii
                    JOIN products p
                        ON p.id=pii.product_id
                    WHERE pii.{{invoice_fk}}=:id
                    ORDER BY pii.id
                """.replace("{{invoice_fk}}",invoice_fk)), {{"id":invoice_id}}).fetchall()
            else:
                items=[]

            result=dict(invoice._mapping)
            result["items"]=[dict(x._mapping) for x in items]

            return result


    @staticmethod
    def supplier_balance(supplier_id):
        with get_session() as s:
            return float(
                s.execute(text("""
                    SELECT COALESCE(current_balance,0)
                    FROM suppliers
                    WHERE id=:id
                """), {{"id":supplier_id}}).scalar() or 0
            )
''',
    encoding="utf-8"
)

# ============================================================
# إصلاح شاشة المشتريات لتستخدم purchase_date
# ============================================================
purchase_window=ROOT/"app/ui/purchases_window.py"

if purchase_window.exists():
    txt=purchase_window.read_text(encoding="utf-8")
    txt=txt.replace(
        'r["created_at"]',
        'r.get("purchase_date","")'
    )
    txt=txt.replace(
        'r["unit_cost"]',
        'r.get("unit_cost", r.get("cost_price", ""))'
    )
    purchase_window.write_text(txt,encoding="utf-8")

con.close()

print("="*70)
print("تم إصلاح توافق طبقة المشتريات مع قاعدة البيانات")
print("="*70)
print("النسخة الاحتياطية:",backup)
print("عمود التاريخ المستخدم:",order_column)
print("[OK] sales_service.py")
print("[OK] purchases_window.py")
print("-"*70)

# ============================================================
# اختبار قاعدة البيانات
# ============================================================
con=sqlite3.connect(DB)
cur=con.cursor()

integrity=cur.execute("PRAGMA integrity_check").fetchone()[0]
fk=len(cur.execute("PRAGMA foreign_key_check").fetchall())

print("SQLite:",integrity)
print("أخطاء العلاقات:",fk)

con.close()

if integrity!="ok" or fk!=0:
    raise SystemExit("فشل فحص سلامة قاعدة البيانات")

print("="*70)
print("تشغيل الاختبارات...")
print("="*70)
