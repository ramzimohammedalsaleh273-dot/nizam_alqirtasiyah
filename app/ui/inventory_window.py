from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QLabel, QMessageBox,
    QHeaderView, QDialog, QFormLayout, QDialogButtonBox, QDoubleSpinBox
from PySide6.QtCore import Qt
from app.services.inventory_service import InventoryService
from app.services.product_service import ProductService


class InventoryWindow(QWidget):
    """واجهة تشغيلية لعرض المخزون والبحث في الأصناف."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("المنتجات والمخزون")
        self.setMinimumSize(1150, 650)

        layout = QVBoxLayout(self)

        title = QLabel("المنتجات والمخزون")
        title.setStyleSheet("font-size:28px;font-weight:bold")
        layout.addWidget(title)

        bar = QHBoxLayout()

        self.search = QLineEdit()
        self.search.setPlaceholderText(
            "ابحث بالباركود أو رمز الصنف أو اسم المنتج..."
        )
        self.search.returnPressed.connect(self.load)

        search_button = QPushButton("بحث")
        search_button.clicked.connect(self.load)

        add_button = QPushButton("إضافة صنف")
        add_button.clicked.connect(self.add_product)
        bar.addWidget(add_button)

        refresh_button = QPushButton("تحديث")
        refresh_button.clicked.connect(lambda: self.load(""))

        bar.addWidget(self.search)
        bar.addWidget(search_button)
        bar.addWidget(refresh_button)
        layout.addLayout(bar)

        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels([
            "المعرف", "رمز الصنف", "اسم المنتج", "تكلفة",
            "سعر البيع", "سعر الجملة", "سعر المدارس",
            "الكمية", "المتاح"
        ])
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.Stretch
        )
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

        self.status = QLabel("جاهز")
        self.status.setStyleSheet("padding:6px")
        layout.addWidget(self.status)

        self.load("")

    def add_product(self):
        dialog=QDialog(self); dialog.setWindowTitle("إضافة صنف جديد")
        form=QFormLayout(dialog)
        sku=QLineEdit(); name=QLineEdit(); barcode=QLineEdit()
        cost=QDoubleSpinBox(); sale=QDoubleSpinBox()
        for x in (cost,sale): x.setMaximum(999999999); x.setDecimals(2)
        form.addRow("رمز الصنف:",sku); form.addRow("اسم المنتج:",name); form.addRow("الباركود:",barcode)
        form.addRow("التكلفة:",cost); form.addRow("سعر البيع:",sale)
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject); form.addRow(buttons)
        if dialog.exec()!=QDialog.Accepted: return
        try:
            ProductService.create_product(sku.text(),name.text(),cost.value(),sale.value(),barcode.text() or None)
            QMessageBox.information(self,"تم","تم إنشاء الصنف بنجاح"); self.load("")
        except Exception as exc: QMessageBox.critical(self,"فشل إنشاء الصنف",str(exc))

    def load(self, term=None):
        if term is None:
            term = self.search.text().strip()
        else:
            term = str(term).strip()
            self.search.setText(term)

        try:
            rows = InventoryService.search_products(term)
            self.table.setRowCount(0)

            for item in rows:
                row = self.table.rowCount()
                self.table.insertRow(row)

                values = [
                    item.get("id", ""),
                    item.get("sku", "") or "",
                    item.get("name_ar", "") or "",
                    item.get("cost_price", 0),
                    item.get("sale_price", 0),
                    item.get("wholesale_price", 0),
                    item.get("school_price", 0),
                    item.get("quantity", 0),
                    item.get("available_quantity", 0),
                ]

                for column, value in enumerate(values):
                    self.table.setItem(
                        row, column, QTableWidgetItem(str(value))
                    )

            self.status.setText(f"تم العثور على {len(rows)} صنف")
        except Exception as exc:
            self.status.setText("تعذر تحميل المخزون")
            QMessageBox.critical(
                self, "خطأ في المخزون", str(exc)
            )
