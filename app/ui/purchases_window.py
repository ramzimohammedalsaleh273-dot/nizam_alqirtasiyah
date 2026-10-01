from app.ui.theme import APP_STYLE

from PySide6.QtWidgets import (
    QWidget,QVBoxLayout,QTableWidget,QTableWidgetItem,
    QPushButton,QHBoxLayout,QLabel,QMessageBox
)
from app.services.purchase_service import PurchaseService

class PurchasesWindow(QWidget):

    def __init__(self,parent=None):
        super().__init__(parent)
        self.setStyleSheet(APP_STYLE)
        self.setStyleSheet(APP_STYLE)
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

# UI reference theme is applied by the main application shell.
