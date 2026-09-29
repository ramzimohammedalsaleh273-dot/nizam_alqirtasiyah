
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
