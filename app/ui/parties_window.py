
from PySide6.QtWidgets import (
    QWidget,QVBoxLayout,QTabWidget,QTableWidget,
    QTableWidgetItem,QLabel,QPushButton,QHBoxLayout,QInputDialog,QMessageBox
)
from app.services.party_service import PartyService
from app.services.party_master_service import PartyMasterService

class PartiesWindow(QWidget):

    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWindowTitle("العملاء والموردون")
        self.setMinimumSize(1000,600)

        layout=QVBoxLayout(self)

        title=QLabel("إدارة الأطراف")
        title.setStyleSheet("font-size:28px;font-weight:bold")
        layout.addWidget(title)

        bar=QHBoxLayout()
        add_customer=QPushButton("إضافة عميل")
        add_supplier=QPushButton("إضافة مورد")
        add_customer.clicked.connect(self.add_customer)
        add_supplier.clicked.connect(self.add_supplier)
        bar.addWidget(add_customer); bar.addWidget(add_supplier); bar.addStretch()
        layout.addLayout(bar)

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

    def add_party_dialog(self, supplier=False):
        code, ok=QInputDialog.getText(self, "إضافة مورد" if supplier else "إضافة عميل", "الكود:")
        if not ok: return
        name, ok=QInputDialog.getText(self, "إضافة طرف", "الاسم:")
        if not ok: return
        phone, ok=QInputDialog.getText(self, "إضافة طرف", "الهاتف (اختياري):")
        if not ok: return
        try:
            if supplier: PartyMasterService.create_supplier(code,name,phone or None)
            else: PartyMasterService.create_customer(code,name,phone or None)
            self.load()
        except Exception as exc: QMessageBox.critical(self,"فشل الحفظ",str(exc))

    def add_customer(self): self.add_party_dialog(False)
    def add_supplier(self): self.add_party_dialog(True)

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
