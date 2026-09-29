from pathlib import Path
import shutil,datetime

ROOT=Path.cwd()
DB=ROOT/"database"/"nizam_alqirtasiyah.db"
BACKUPS=ROOT/"database"/"backups"
BACKUPS.mkdir(parents=True,exist_ok=True)

stamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup=BACKUPS/f"nizam_alqirtasiyah_before_pos_core_{stamp}.db"
if DB.exists():
    shutil.copy2(DB,backup)

for d in ["app/services","app/ui","tests"]:
    (ROOT/d).mkdir(parents=True,exist_ok=True)

# ============================================================
# خدمة المنتجات والمخزون
# ============================================================
(ROOT/"app/services/inventory_service.py").write_text(r'''
from sqlalchemy import text
from app.database.connection import get_session

class InventoryService:

    @staticmethod
    def search_products(term=""):
        with get_session() as s:
            q = """
            SELECT
                p.id,p.sku,p.name_ar,p.cost_price,p.sale_price,
                p.wholesale_price,p.school_price,p.corporate_price,
                COALESCE(st.quantity,0) AS quantity,
                COALESCE(st.available_quantity,0) AS available_quantity
            FROM products p
            LEFT JOIN stock st ON st.product_id=p.id
            WHERE p.is_active=1
            """
            params={}
            if term:
                q += """
                AND (
                    p.name_ar LIKE :term
                    OR p.name_en LIKE :term
                    OR p.sku LIKE :term
                    OR EXISTS(
                        SELECT 1 FROM product_barcodes pb
                        WHERE pb.product_id=p.id
                        AND pb.barcode LIKE :term
                    )
                )
                """
                params["term"]=f"%{term}%"

            q += " ORDER BY p.id LIMIT 100"

            return [dict(r._mapping) for r in s.execute(
                text(q),params
            ).fetchall()]

    @staticmethod
    def get_product(product_id):
        with get_session() as s:
            r=s.execute(text("""
                SELECT
                    p.*,
                    COALESCE(st.quantity,0) quantity,
                    COALESCE(st.available_quantity,0) available_quantity,
                    COALESCE(st.average_cost,0) average_cost
                FROM products p
                LEFT JOIN stock st ON st.product_id=p.id
                WHERE p.id=:id
            """),{"id":product_id}).fetchone()

            return dict(r._mapping) if r else None

    @staticmethod
    def available_quantity(product_id,warehouse_id=1):
        with get_session() as s:
            return float(s.execute(text("""
                SELECT COALESCE(available_quantity,0)
                FROM stock
                WHERE product_id=:p AND warehouse_id=:w
            """),{"p":product_id,"w":warehouse_id}).scalar() or 0)
''',encoding="utf-8")

# ============================================================
# خدمة نقطة البيع
# ============================================================
(ROOT/"app/services/pos_service.py").write_text(r'''
from decimal import Decimal
from sqlalchemy import text
from app.database.connection import get_session

class POSService:

    @staticmethod
    def create_sale(
        items,
        payment_method="cash",
        customer_id=None,
        warehouse_id=1,
        branch_id=1,
        cashier_id=None
    ):
        if not items:
            raise ValueError("لا توجد أصناف في الفاتورة")

        with get_session() as s:
            try:
                subtotal=Decimal("0")
                prepared=[]

                for item in items:
                    product_id=int(item["product_id"])
                    quantity=Decimal(str(item["quantity"]))

                    if quantity <= 0:
                        raise ValueError("الكمية يجب أن تكون أكبر من صفر")

                    p=s.execute(text("""
                        SELECT id,name_ar,sale_price
                        FROM products
                        WHERE id=:id AND is_active=1
                    """),{"id":product_id}).fetchone()

                    if not p:
                        raise ValueError(f"الصنف غير موجود: {product_id}")

                    stock=s.execute(text("""
                        SELECT COALESCE(available_quantity,0)
                        FROM stock
                        WHERE product_id=:p AND warehouse_id=:w
                    """),{"p":product_id,"w":warehouse_id}).scalar()

                    available=Decimal(str(stock or 0))

                    if available < quantity:
                        raise ValueError(
                            f"المخزون غير كاف للصنف: {p.name_ar} "
                            f"(المتاح {available})"
                        )

                    price=Decimal(str(
                        item.get("unit_price",p.sale_price)
                    ))

                    discount=Decimal(str(item.get("discount",0)))
                    line=(quantity*price)-discount

                    if line < 0:
                        raise ValueError("قيمة السطر لا يمكن أن تكون سالبة")

                    subtotal += line

                    prepared.append({
                        "product_id":product_id,
                        "quantity":quantity,
                        "unit_price":price,
                        "discount":discount,
                        "line_total":line,
                    })

                # ضريبة 15%
                tax=(subtotal*Decimal("0.15")).quantize(Decimal("0.01"))
                total=subtotal+tax

                count=s.execute(text("""
                    SELECT COUNT(*) FROM sales
                """)).scalar()

                invoice=f"INV-2026-{int(count)+1:06d}"

                s.execute(text("""
                    INSERT INTO sales
                    (
                        invoice_number,branch_id,warehouse_id,customer_id,
                        cashier_id,status,subtotal,discount_amount,
                        tax_amount,total_amount,paid_amount,due_amount,
                        notes,created_at
                    )
                    VALUES
                    (
                        :invoice,:branch,:warehouse,:customer,
                        :cashier,'POSTED',:subtotal,:discount,
                        :tax,:total,:paid,:due,
                        :notes,CURRENT_TIMESTAMP
                    )
                """),{
                    "invoice":invoice,
                    "branch":branch_id,
                    "warehouse":warehouse_id,
                    "customer":customer_id,
                    "cashier":cashier_id,
                    "subtotal":float(subtotal),
                    "discount":float(sum(x["discount"] for x in prepared)),
                    "tax":float(tax),
                    "total":float(total),
                    "paid":float(total),
                    "due":0,
                    "notes":"فاتورة نقطة بيع",
                })

                sale_id=s.execute(
                    text("SELECT last_insert_rowid()")
                ).scalar()

                for item in prepared:
                    s.execute(text("""
                        INSERT INTO sale_items
                        (sale_id,product_id,quantity,unit_price,
                         discount_amount,tax_amount,line_total)
                        VALUES
                        (:sale,:product,:qty,:price,
                         :discount,0,:line)
                    """),{
                        "sale":sale_id,
                        "product":item["product_id"],
                        "qty":float(item["quantity"]),
                        "price":float(item["unit_price"]),
                        "discount":float(item["discount"]),
                        "line":float(item["line_total"]),
                    })

                    cost=s.execute(text("""
                        SELECT COALESCE(average_cost,0)
                        FROM stock
                        WHERE product_id=:p AND warehouse_id=:w
                    """),{
                        "p":item["product_id"],
                        "w":warehouse_id
                    }).scalar() or 0

                    s.execute(text("""
                        UPDATE stock
                        SET quantity=quantity-:q,
                            available_quantity=available_quantity-:q,
                            updated_at=CURRENT_TIMESTAMP
                        WHERE product_id=:p AND warehouse_id=:w
                    """),{
                        "q":float(item["quantity"]),
                        "p":item["product_id"],
                        "w":warehouse_id
                    })

                    s.execute(text("""
                        INSERT INTO stock_movements
                        (
                            product_id,warehouse_id,movement_type,
                            quantity,unit_cost,reference_type,
                            reference_id,notes,created_at
                        )
                        VALUES
                        (:p,:w,'SALE',:q,:cost,'SALE',
                         :sale,'صرف مخزون من نقطة البيع',CURRENT_TIMESTAMP)
                    """),{
                        "p":item["product_id"],
                        "w":warehouse_id,
                        "q":-float(item["quantity"]),
                        "cost":float(cost),
                        "sale":sale_id
                    })

                s.commit()

                return {
                    "sale_id":sale_id,
                    "invoice_number":invoice,
                    "subtotal":float(subtotal),
                    "tax":float(tax),
                    "total":float(total),
                    "payment_method":payment_method
                }

            except:
                s.rollback()
                raise
''',encoding="utf-8")

# ============================================================
# واجهة نقطة البيع
# ============================================================
(ROOT/"app/ui/pos_window.py").write_text(r'''
from PySide6.QtWidgets import (
    QWidget,QVBoxLayout,QHBoxLayout,QLineEdit,QPushButton,
    QTableWidget,QTableWidgetItem,QLabel,QMessageBox,
    QHeaderView
)
from PySide6.QtCore import Qt
from app.services.inventory_service import InventoryService
from app.services.pos_service import POSService

class POSWindow(QWidget):

    def __init__(self,parent=None):
        super().__init__(parent)

        self.cart=[]

        self.setWindowTitle("نقطة البيع")
        self.setMinimumSize(1100,650)

        layout=QVBoxLayout(self)

        title=QLabel("نقطة البيع")
        title.setStyleSheet("font-size:28px;font-weight:bold")
        layout.addWidget(title)

        top=QHBoxLayout()

        self.search=QLineEdit()
        self.search.setPlaceholderText(
            "ابحث بالباركود أو رمز الصنف أو اسم المنتج..."
        )
        self.search.returnPressed.connect(self.add_search_result)

        add=QPushButton("إضافة")
        add.clicked.connect(self.add_search_result)

        top.addWidget(self.search)
        top.addWidget(add)

        layout.addLayout(top)

        self.table=QTableWidget(0,5)
        self.table.setHorizontalHeaderLabels([
            "الصنف","الكمية","السعر","الخصم","الإجمالي"
        ])
        self.table.horizontalHeader().setSectionResizeMode(
            0,QHeaderView.Stretch
        )
        layout.addWidget(self.table)

        bottom=QHBoxLayout()

        self.total=QLabel("الإجمالي: 0.00")
        self.total.setStyleSheet(
            "font-size:22px;font-weight:bold"
        )

        pay=QPushButton("دفع نقدي وإتمام البيع")
        pay.clicked.connect(self.complete_sale)

        bottom.addWidget(self.total)
        bottom.addStretch()
        bottom.addWidget(pay)

        layout.addLayout(bottom)

    def add_search_result(self):
        term=self.search.text().strip()
        if not term:
            return

        products=InventoryService.search_products(term)

        if not products:
            QMessageBox.warning(
                self,"غير موجود","لم يتم العثور على الصنف"
            )
            return

        p=products[0]

        for item in self.cart:
            if item["product_id"]==p["id"]:
                item["quantity"]+=1
                self.refresh()
                self.search.clear()
                return

        self.cart.append({
            "product_id":p["id"],
            "name":p["name_ar"],
            "quantity":1,
            "unit_price":float(p["sale_price"]),
            "discount":0,
        })

        self.refresh()
        self.search.clear()

    def refresh(self):
        self.table.setRowCount(0)
        total=0

        for item in self.cart:
            row=self.table.rowCount()
            self.table.insertRow(row)

            line=(
                item["quantity"]*
                item["unit_price"]
            )-item["discount"]

            total+=line

            values=[
                item["name"],
                item["quantity"],
                f'{item["unit_price"]:.2f}',
                f'{item["discount"]:.2f}',
                f'{line:.2f}',
            ]

            for col,value in enumerate(values):
                self.table.setItem(
                    row,col,QTableWidgetItem(str(value))
                )

        tax=total*0.15
        grand=total+tax

        self.total.setText(
            f"الإجمالي مع الضريبة: {grand:.2f}"
        )

    def complete_sale(self):
        if not self.cart:
            QMessageBox.warning(
                self,"تنبيه","الفاتورة فارغة"
            )
            return

        try:
            result=POSService.create_sale(
                self.cart,
                payment_method="cash"
            )

            QMessageBox.information(
                self,
                "تمت العملية",
                f"تم إنشاء الفاتورة\n"
                f"{result['invoice_number']}\n"
                f"الإجمالي: {result['total']:.2f}"
            )

            self.cart=[]
            self.refresh()

        except Exception as e:
            QMessageBox.critical(
                self,
                "فشل البيع",
                str(e)
            )
''',encoding="utf-8")

# ============================================================
# اختبار الخدمات بدون إنشاء عملية بيع حقيقية
# ============================================================
(ROOT/"tests"/"test_pos_core.py").write_text(r'''
from app.services.inventory_service import InventoryService

def test_product_search():
    products=InventoryService.search_products("دفتر")
    assert isinstance(products,list)

def test_product_exists():
    product=InventoryService.get_product(1)
    assert product is not None
    assert product["id"]==1

def test_stock_available():
    quantity=InventoryService.available_quantity(1,1)
    assert quantity >= 0
''',encoding="utf-8")

print("="*70)
print("تم بناء نواة نقطة البيع والمخزون")
print("="*70)
print("النسخة الاحتياطية:",backup)
print("[OK] inventory_service.py")
print("[OK] pos_service.py")
print("[OK] pos_window.py")
print("[OK] test_pos_core.py")
print("="*70)
