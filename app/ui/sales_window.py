
from PySide6.QtWidgets import (
    QWidget,QVBoxLayout,QTableWidget,QTableWidgetItem,
    QPushButton,QHBoxLayout,QLabel,QMessageBox
)
from PySide6.QtCore import Qt
from app.services.sales_service import SalesService

class SalesWindow(QWidget):

    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWindowTitle("المبيعات والفواتير")
        self.setMinimumSize(1250,720)

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
