
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
