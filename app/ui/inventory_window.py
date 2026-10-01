from app.ui.theme import APP_STYLE
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QLabel, QMessageBox,
    QHeaderView, QDialog, QFormLayout, QDialogButtonBox, QDoubleSpinBox, QComboBox
)
from PySide6.QtCore import Qt
from app.services.inventory_service import InventoryService
from app.services.product_service import ProductService


class InventoryWindow(QWidget):
    """واجهة تشغيلية لعرض المخزون والبحث في الأصناف."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(APP_STYLE)
        self.setWindowTitle("المنتجات والمخزون")
        self.setMinimumSize(1150, 650)

        layout = QVBoxLayout(self)
        self.setLayoutDirection(Qt.RightToLeft)

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
        edit_button = QPushButton("تعديل الصنف")
        edit_button.clicked.connect(self.edit_product)
        delete_button = QPushButton("تعطيل/حذف الصنف")
        delete_button.clicked.connect(self.delete_product)
        bar.addWidget(add_button)
        bar.addWidget(edit_button)
        bar.addWidget(delete_button)

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
        self.table.setWordWrap(False)
        self.table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
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
        cost=QDoubleSpinBox(); sale=QDoubleSpinBox(); opening=QDoubleSpinBox(); warehouse=QComboBox()
        for x in (cost,sale,opening): x.setMaximum(999999999); x.setDecimals(2)
        opening.setMinimum(0)
        try:
            from app.database.connection import get_session
            from sqlalchemy import text
            with get_session() as s:
                for r in s.execute(text("SELECT id,name FROM warehouses WHERE COALESCE(is_active,1)=1 ORDER BY id")).mappings():
                    warehouse.addItem(str(r["name"]), int(r["id"]))
        except Exception:
            warehouse.addItem("المستودع الافتراضي",1)
        form.addRow("رمز الصنف:",sku); form.addRow("اسم المنتج:",name); form.addRow("الباركود:",barcode)
        form.addRow("التكلفة:",cost); form.addRow("سعر البيع:",sale); form.addRow("الكمية الافتتاحية:",opening); form.addRow("المستودع:",warehouse)
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject); form.addRow(buttons)
        if dialog.exec()!=QDialog.Accepted: return
        try:
            ProductService.create_product(sku.text(),name.text(),cost.value(),sale.value(),barcode.text() or None,opening.value(),warehouse.currentData() or 1)
            QMessageBox.information(self,"تم","تم إنشاء الصنف بنجاح"); self.load("")
        except Exception as exc: QMessageBox.critical(self,"فشل إنشاء الصنف",str(exc))

    def edit_product(self):
        row=self.table.currentRow()
        if row<0:
            QMessageBox.warning(self,"تنبيه","اختر صنفًا أولاً"); return
        product_id=int(self.table.item(row,0).text())
        sku=QLineEdit(self.table.item(row,1).text())
        name=QLineEdit(self.table.item(row,2).text())
        cost=QDoubleSpinBox(); sale=QDoubleSpinBox(); quantity=QDoubleSpinBox(); warehouse=QComboBox()
        cost.setMaximum(999999999); sale.setMaximum(999999999); cost.setDecimals(2); sale.setDecimals(2)
        try:
            from app.database.connection import get_session
            from sqlalchemy import text
            with get_session() as s:
                for r in s.execute(text("SELECT id,name FROM warehouses WHERE COALESCE(is_active,1)=1 ORDER BY id")).mappings():
                    warehouse.addItem(str(r["name"]), int(r["id"]))
        except Exception:
            warehouse.addItem("المستودع الافتراضي",1)
        cost.setValue(float(self.table.item(row,3).text() or 0)); sale.setValue(float(self.table.item(row,4).text() or 0))
        quantity.setValue(0)
        def load_selected_warehouse_quantity():
            try:
                from app.database.connection import get_session
                from sqlalchemy import text
                with get_session() as s:
                    current=s.execute(text("SELECT COALESCE(quantity,0) FROM stock WHERE product_id=:p AND warehouse_id=:w"), {"p":product_id,"w":int(warehouse.currentData() or 1)}).scalar()
                    quantity.setValue(float(current or 0))
            except Exception:
                quantity.setValue(0)
        warehouse.currentIndexChanged.connect(load_selected_warehouse_quantity)
        load_selected_warehouse_quantity()
        dialog=QDialog(self); dialog.setWindowTitle("تعديل الصنف"); form=QFormLayout(dialog)
        form.addRow("رمز الصنف:",sku); form.addRow("اسم المنتج:",name); form.addRow("التكلفة:",cost); form.addRow("سعر البيع:",sale); form.addRow("الكمية الحالية:",quantity); form.addRow("المستودع:",warehouse)
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel); buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject); form.addRow(buttons)
        if dialog.exec()!=QDialog.Accepted: return
        try:
            ProductService.update_product(product_id,sku.text(),name.text(),cost.value(),sale.value())
            ProductService.adjust_quantity(product_id, warehouse.currentData() or 1, quantity.value())
            self.load(self.search.text().strip()); QMessageBox.information(self,"تم","تم تحديث الصنف بنجاح")
        except Exception as exc: QMessageBox.critical(self,"فشل التعديل",str(exc))

    def delete_product(self):
        row=self.table.currentRow()
        if row<0:
            QMessageBox.warning(self,"تنبيه","اختر صنفًا أولًا"); return
        product_id=int(self.table.item(row,0).text())
        if QMessageBox.question(self,"تعطيل الصنف","سيتم إخفاؤه من التشغيل مع الاحتفاظ بتاريخه. هل تريد المتابعة؟",QMessageBox.Yes|QMessageBox.No)!=QMessageBox.Yes: return
        try:
            ProductService.deactivate_product(product_id)
            self.load(self.search.text().strip())
        except Exception as exc:
            QMessageBox.critical(self,"فشل تعطيل الصنف",str(exc))

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

            self.status.setText(f"تم العثور على {len(rows)} صنف — الكميات المعروضة إجمالية، والتعديل يتم على مستودع محدد.")
        except Exception as exc:
            self.status.setText("تعذر تحميل المخزون")
            QMessageBox.critical(
                self, "خطأ في المخزون", str(exc)
            )

# UI reference theme is applied by the main application shell.
