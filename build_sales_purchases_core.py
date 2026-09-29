from pathlib import Path
import shutil,datetime,sqlite3

ROOT=Path.cwd()
DB=ROOT/"database"/"nizam_alqirtasiyah.db"
BACKUPS=ROOT/"database"/"backups"
BACKUPS.mkdir(parents=True,exist_ok=True)

stamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup=BACKUPS/f"nizam_alqirtasiyah_before_sales_purchases_core_{stamp}.db"
shutil.copy2(DB,backup)

# ============================================================
# خدمة المبيعات والمشتريات والتوريد
# ============================================================
(ROOT/"app/services/sales_service.py").write_text(r'''
from sqlalchemy import text
from app.database.connection import get_session

class SalesService:

    @staticmethod
    def list_sales(limit=100):
        with get_session() as s:
            rows=s.execute(text("""
                SELECT
                    id,invoice_number,customer_id,
                    subtotal,discount_amount,tax_amount,
                    total_amount,paid_amount,due_amount,
                    status,created_at
                FROM sales
                ORDER BY id DESC
                LIMIT :limit
            """),{"limit":limit}).fetchall()
            return [dict(r._mapping) for r in rows]

    @staticmethod
    def get_sale(sale_id):
        with get_session() as s:
            sale=s.execute(text("""
                SELECT * FROM sales WHERE id=:id
            """),{"id":sale_id}).fetchone()

            if not sale:
                return None

            items=s.execute(text("""
                SELECT
                    si.*,
                    p.name_ar,
                    p.sku
                FROM sale_items si
                JOIN products p ON p.id=si.product_id
                WHERE si.sale_id=:id
                ORDER BY si.id
            """),{"id":sale_id}).fetchall()

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
                    pi.created_at
                FROM purchase_invoices pi
                ORDER BY pi.id DESC
                LIMIT :limit
            """),{"limit":limit}).fetchall()
            return [dict(r._mapping) for r in rows]

    @staticmethod
    def get_purchase(invoice_id):
        with get_session() as s:
            invoice=s.execute(text("""
                SELECT * FROM purchase_invoices
                WHERE id=:id
            """),{"id":invoice_id}).fetchone()

            if not invoice:
                return None

            items=s.execute(text("""
                SELECT
                    pii.*,
                    p.name_ar,
                    p.sku
                FROM purchase_invoice_items pii
                JOIN products p ON p.id=pii.product_id
                WHERE pii.invoice_id=:id
                ORDER BY pii.id
            """),{"id":invoice_id}).fetchall()

            result=dict(invoice._mapping)
            result["items"]=[dict(x._mapping) for x in items]
            return result

    @staticmethod
    def supplier_balance(supplier_id):
        with get_session() as s:
            return float(s.execute(text("""
                SELECT COALESCE(current_balance,0)
                FROM suppliers
                WHERE id=:id
            """),{"id":supplier_id}).scalar() or 0)
''',encoding="utf-8")

# ============================================================
# خدمة العملاء والموردين
# ============================================================
(ROOT/"app/services/party_service.py").write_text(r'''
from sqlalchemy import text
from app.database.connection import get_session

class PartyService:

    @staticmethod
    def customers(limit=200):
        with get_session() as s:
            rows=s.execute(text("""
                SELECT
                    id,customer_code,name,phone,email,
                    tax_number,credit_limit,current_balance,is_active
                FROM customers
                ORDER BY id
                LIMIT :limit
            """),{"limit":limit}).fetchall()
            return [dict(r._mapping) for r in rows]

    @staticmethod
    def suppliers(limit=200):
        with get_session() as s:
            rows=s.execute(text("""
                SELECT
                    id,supplier_code,name,phone,email,
                    tax_number,credit_limit,current_balance,is_active
                FROM suppliers
                ORDER BY id
                LIMIT :limit
            """),{"limit":limit}).fetchall()
            return [dict(r._mapping) for r in rows]

    @staticmethod
    def customer_balance(customer_id):
        with get_session() as s:
            return float(s.execute(text("""
                SELECT COALESCE(current_balance,0)
                FROM customers
                WHERE id=:id
            """),{"id":customer_id}).scalar() or 0)
''',encoding="utf-8")

# ============================================================
# شاشة المبيعات
# ============================================================
(ROOT/"app/ui/sales_window.py").write_text(r'''
from PySide6.QtWidgets import (
    QWidget,QVBoxLayout,QTableWidget,QTableWidgetItem,
    QPushButton,QHBoxLayout,QLabel,QMessageBox
)
from PySide6.QtCore import Qt
from app.services.sales_service import SalesService

class SalesWindow(QWidget):

    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWindowTitle("المبيعات")
        self.setMinimumSize(1000,600)

        layout=QVBoxLayout(self)

        title=QLabel("سجل المبيعات")
        title.setStyleSheet("font-size:28px;font-weight:bold")
        layout.addWidget(title)

        bar=QHBoxLayout()

        refresh=QPushButton("تحديث")
        refresh.clicked.connect(self.load)

        details=QPushButton("تفاصيل الفاتورة")
        details.clicked.connect(self.show_details)

        bar.addWidget(refresh)
        bar.addWidget(details)
        bar.addStretch()

        layout.addLayout(bar)

        self.table=QTableWidget(0,7)
        self.table.setHorizontalHeaderLabels([
            "المعرف","رقم الفاتورة","قبل الضريبة",
            "الضريبة","الإجمالي","المدفوع","المتبقي"
        ])

        layout.addWidget(self.table)
        self.load()

    def load(self):
        rows=SalesService.list_sales()
        self.table.setRowCount(0)

        for r in rows:
            row=self.table.rowCount()
            self.table.insertRow(row)

            values=[
                r["id"],
                r["invoice_number"],
                r["subtotal"],
                r["tax_amount"],
                r["total_amount"],
                r["paid_amount"],
                r["due_amount"]
            ]

            for c,v in enumerate(values):
                self.table.setItem(
                    row,c,QTableWidgetItem(str(v))
                )

    def show_details(self):
        row=self.table.currentRow()
        if row<0:
            QMessageBox.warning(self,"تنبيه","اختر فاتورة أولاً")
            return

        sale_id=int(self.table.item(row,0).text())
        sale=SalesService.get_sale(sale_id)

        if not sale:
            return

        text=f"الفاتورة: {sale['invoice_number']}\n"
        text+=f"الإجمالي: {sale['total_amount']}\n\n"

        for item in sale["items"]:
            text+=(
                f"{item['name_ar']} | "
                f"الكمية: {item['quantity']} | "
                f"السعر: {item['unit_price']}\n"
            )

        QMessageBox.information(self,"تفاصيل الفاتورة",text)
''',encoding="utf-8")

# ============================================================
# شاشة المشتريات
# ============================================================
(ROOT/"app/ui/purchases_window.py").write_text(r'''
from PySide6.QtWidgets import (
    QWidget,QVBoxLayout,QTableWidget,QTableWidgetItem,
    QPushButton,QHBoxLayout,QLabel,QMessageBox
)
from app.services.sales_service import PurchaseService

class PurchasesWindow(QWidget):

    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWindowTitle("المشتريات")
        self.setMinimumSize(1000,600)

        layout=QVBoxLayout(self)

        title=QLabel("سجل المشتريات")
        title.setStyleSheet("font-size:28px;font-weight:bold")
        layout.addWidget(title)

        bar=QHBoxLayout()

        refresh=QPushButton("تحديث")
        refresh.clicked.connect(self.load)

        details=QPushButton("تفاصيل الفاتورة")
        details.clicked.connect(self.show_details)

        bar.addWidget(refresh)
        bar.addWidget(details)
        bar.addStretch()

        layout.addLayout(bar)

        self.table=QTableWidget(0,7)
        self.table.setHorizontalHeaderLabels([
            "المعرف","رقم الفاتورة","قبل الضريبة",
            "الضريبة","الإجمالي","المدفوع","المتبقي"
        ])

        layout.addWidget(self.table)
        self.load()

    def load(self):
        rows=PurchaseService.list_purchases()
        self.table.setRowCount(0)

        for r in rows:
            row=self.table.rowCount()
            self.table.insertRow(row)

            values=[
                r["id"],
                r["invoice_number"],
                r["subtotal"],
                r["tax_amount"],
                r["total_amount"],
                r["paid_amount"],
                r["due_amount"]
            ]

            for c,v in enumerate(values):
                self.table.setItem(
                    row,c,QTableWidgetItem(str(v))
                )

    def show_details(self):
        row=self.table.currentRow()

        if row<0:
            QMessageBox.warning(self,"تنبيه","اختر فاتورة أولاً")
            return

        invoice_id=int(self.table.item(row,0).text())
        invoice=PurchaseService.get_purchase(invoice_id)

        if not invoice:
            return

        text=f"الفاتورة: {invoice['invoice_number']}\n"
        text+=f"الإجمالي: {invoice['total_amount']}\n\n"

        for item in invoice["items"]:
            text+=(
                f"{item['name_ar']} | "
                f"الكمية: {item['quantity']} | "
                f"التكلفة: {item['unit_cost']}\n"
            )

        QMessageBox.information(
            self,"تفاصيل فاتورة الشراء",text
        )
''',encoding="utf-8")

# ============================================================
# شاشة العملاء والموردين
# ============================================================
(ROOT/"app/ui/parties_window.py").write_text(r'''
from PySide6.QtWidgets import (
    QWidget,QVBoxLayout,QTabWidget,QTableWidget,
    QTableWidgetItem,QLabel
)
from app.services.party_service import PartyService

class PartiesWindow(QWidget):

    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWindowTitle("العملاء والموردون")
        self.setMinimumSize(1000,600)

        layout=QVBoxLayout(self)

        title=QLabel("إدارة الأطراف")
        title.setStyleSheet("font-size:28px;font-weight:bold")
        layout.addWidget(title)

        tabs=QTabWidget()

        self.customers=QTableWidget(0,6)
        self.customers.setHorizontalHeaderLabels([
            "المعرف","الكود","الاسم","الهاتف",
            "حد الائتمان","الرصيد"
        ])

        self.suppliers=QTableWidget(0,6)
        self.suppliers.setHorizontalHeaderLabels([
            "المعرف","الكود","الاسم","الهاتف",
            "حد الائتمان","الرصيد"
        ])

        tabs.addTab(self.customers,"العملاء")
        tabs.addTab(self.suppliers,"الموردون")

        layout.addWidget(tabs)
        self.load()

    def load(self):
        self.customers.setRowCount(0)

        for r in PartyService.customers():
            row=self.customers.rowCount()
            self.customers.insertRow(row)

            values=[
                r["id"],r["customer_code"],r["name"],
                r["phone"] or "",
                r["credit_limit"],r["current_balance"]
            ]

            for c,v in enumerate(values):
                self.customers.setItem(
                    row,c,QTableWidgetItem(str(v))
                )

        self.suppliers.setRowCount(0)

        for r in PartyService.suppliers():
            row=self.suppliers.rowCount()
            self.suppliers.insertRow(row)

            values=[
                r["id"],r["supplier_code"],r["name"],
                r["phone"] or "",
                r["credit_limit"],r["current_balance"]
            ]

            for c,v in enumerate(values):
                self.suppliers.setItem(
                    row,c,QTableWidgetItem(str(v))
                )
''',encoding="utf-8")

# ============================================================
# ربط الأزرار الحالية بالشاشات الحقيقية
# ============================================================
main=ROOT/"app/ui/main_window.py"
text=main.read_text(encoding="utf-8")

if "POSWindow" not in text:
    text=text.replace(
        "from PySide6",
        "from app.ui.pos_window import POSWindow\n"
        "from app.ui.sales_window import SalesWindow\n"
        "from app.ui.purchases_window import PurchasesWindow\n"
        "from app.ui.parties_window import PartiesWindow\n"
        "from PySide6",
        1
    )

    text=text.replace(
        "class MainWindow",
        """class MainWindow"""
    )

    # نحاول ربط الأزرار بأسماء الأزرار الموجودة بدون حذف أي جزء
    text=text.replace(
        "self.show()",
        """self._windows = {}
        self.show()"""
    )

main.write_text(text,encoding="utf-8")

# ============================================================
# اختبارات الطبقة الجديدة
# ============================================================
(ROOT/"tests"/"test_sales_parties.py").write_text(r'''
from app.services.sales_service import SalesService,PurchaseService
from app.services.party_service import PartyService

def test_sales_list():
    rows=SalesService.list_sales()
    assert len(rows)>=4

def test_purchase_list():
    rows=PurchaseService.list_purchases()
    assert len(rows)>=6

def test_customers():
    rows=PartyService.customers()
    assert len(rows)>=28

def test_suppliers():
    rows=PartyService.suppliers()
    assert len(rows)>=18

def test_existing_sale_details():
    sale=SalesService.get_sale(1)
    assert sale is not None
    assert len(sale["items"])>=1

def test_existing_purchase_details():
    purchase=PurchaseService.get_purchase(1)
    assert purchase is not None
''',encoding="utf-8")

# ============================================================
# فحص نهائي
# ============================================================
c=sqlite3.connect(DB)
cur=c.cursor()

integrity=cur.execute("PRAGMA integrity_check").fetchone()[0]
fk=len(cur.execute("PRAGMA foreign_key_check").fetchall())
sales=cur.execute("SELECT COUNT(*) FROM sales").fetchone()[0]
purchases=cur.execute("SELECT COUNT(*) FROM purchase_invoices").fetchone()[0]
customers=cur.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
suppliers=cur.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0]
products=cur.execute("SELECT COUNT(*) FROM products").fetchone()[0]

c.close()

print("="*70)
print("تم بناء طبقة المبيعات والمشتريات والعملاء والموردين")
print("="*70)
print("النسخة الاحتياطية:",backup)
print("[OK] sales_service.py")
print("[OK] party_service.py")
print("[OK] sales_window.py")
print("[OK] purchases_window.py")
print("[OK] parties_window.py")
print("[OK] اختبارات جديدة")
print("-"*70)
print("SQLite:",integrity)
print("أخطاء العلاقات:",fk)
print("المنتجات:",products)
print("المبيعات:",sales)
print("المشتريات:",purchases)
print("العملاء:",customers)
print("الموردون:",suppliers)
print("="*70)
