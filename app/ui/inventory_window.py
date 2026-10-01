from app.ui.theme import APP_STYLE
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QLabel, QMessageBox,
    QHeaderView, QDialog, QFormLayout, QDialogButtonBox, QDoubleSpinBox, QComboBox,
    QTabWidget, QAbstractItemView
)
from sqlalchemy import text
from app.database.connection import get_session
from PySide6.QtCore import Qt
from app.services.inventory_service import InventoryService
from app.services.product_service import ProductService



class ProductCardDialog(QDialog):
    """بطاقة الصنف المرجعية: بيانات وأسعار وباركود ومخزون وحركات ومبيعات ومشتريات وموردون وملاحظات."""
    def __init__(self, product_id, parent=None):
        super().__init__(parent)
        self.product_id=int(product_id)
        self.setWindowTitle("بطاقة الصنف")
        self.setMinimumSize(1180,760)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setStyleSheet(APP_STYLE)
        root=QVBoxLayout(self)
        self.title=QLabel("بطاقة الصنف"); self.title.setObjectName("SectionTitle"); root.addWidget(self.title)
        self.meta=QLabel(""); root.addWidget(self.meta)
        self.tabs=QTabWidget(); root.addWidget(self.tabs,1)
        self._build()

    def _query(self, sql, params):
        with get_session() as s:
            return s.execute(text(sql), params).mappings().all()

    def _table(self, headers, rows):
        t=QTableWidget(0,len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.setSelectionBehavior(QAbstractItemView.SelectRows)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.setAlternatingRowColors(True)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        t.horizontalHeader().setStretchLastSection(True)
        for row in rows:
            r=t.rowCount(); t.insertRow(r)
            for col,v in enumerate(row):
                t.setItem(r,col,QTableWidgetItem("" if v is None else str(v)))
        return t

    def _add_tab(self, title, headers, rows):
        self.tabs.addTab(self._table(headers,rows),title)

    def _build(self):
        with get_session() as s:
            product=s.execute(text("SELECT * FROM products WHERE id=:id"),{"id":self.product_id}).mappings().first()
        if not product:
            self.title.setText("الصنف غير موجود"); return
        self.title.setText(f"بطاقة الصنف: {product.get('name_ar') or product.get('name_en') or '—'}")
        barcode=product.get("barcode") or self._query("SELECT barcode FROM product_barcodes WHERE product_id=:id AND is_primary=1 ORDER BY id LIMIT 1",{"id":self.product_id})
        self.meta.setText(f"المعرف: {product.get('id')}   |   الكود: {product.get('sku') or '—'}   |   الباركود: {(barcode[0].get('barcode') if barcode else '—')}")
        basic=[(k,v) for k,v in product.items() if k not in {"id","created_at","updated_at","description","notes"}]
        self._add_tab("البيانات",["الحقل","القيمة"],basic)
        prices=[("سعر التكلفة",product.get("cost_price")),("سعر البيع",product.get("sale_price")),("سعر الجملة",product.get("wholesale_price")),("سعر المدارس",product.get("school_price")),("سعر الشركات",product.get("corporate_price")),("أقل سعر",product.get("min_price"))]
        self._add_tab("الأسعار",["السعر","القيمة"],prices)
        barcodes=self._query("SELECT barcode,is_primary FROM product_barcodes WHERE product_id=:id ORDER BY id",{"id":self.product_id})
        self._add_tab("الباركود",["الباركود","أساسي"],[(x.get("barcode"),x.get("is_primary")) for x in barcodes])
        stock=self._query("SELECT w.name,sb.quantity,sb.reserved_quantity,sb.quantity-sb.reserved_quantity,sb.average_cost,sb.last_movement_at FROM stock_balances sb JOIN warehouses w ON w.id=sb.warehouse_id WHERE sb.product_id=:id ORDER BY w.name",{"id":self.product_id})
        self._add_tab("المخزون",["المستودع","الكمية","محجوز","المتاح","متوسط التكلفة","آخر حركة"],[(x.get("name"),x.get("quantity"),x.get("reserved_quantity"),x.get("quantity")-x.get("reserved_quantity"),x.get("average_cost"),x.get("last_movement_at")) for x in stock])
        moves=self._query("SELECT sm.created_at,sm.movement_type,sm.reference_type,sm.reference_id,sm.quantity,sm.unit_cost,w.name FROM stock_movements sm LEFT JOIN warehouses w ON w.id=sm.warehouse_id WHERE sm.product_id=:id ORDER BY sm.id DESC LIMIT 500",{"id":self.product_id})
        self._add_tab("الحركات",["التاريخ","الحركة","المصدر","المرجع","الكمية","التكلفة","المستودع"],[(x.get("created_at"),x.get("movement_type"),x.get("reference_type"),x.get("reference_id"),x.get("quantity"),x.get("unit_cost"),x.get("name")) for x in moves])
        sales=self._query("SELECT s.created_at,s.invoice_number,si.quantity,si.unit_price,si.line_total FROM sale_items si JOIN sales s ON s.id=si.sale_id WHERE si.product_id=:id ORDER BY s.id DESC LIMIT 500",{"id":self.product_id})
        self._add_tab("المبيعات",["التاريخ","الفاتورة","الكمية","السعر","الإجمالي"],[(x.get("created_at"),x.get("invoice_number"),x.get("quantity"),x.get("unit_price"),x.get("line_total")) for x in sales])
        purchases=self._query("SELECT pi.invoice_date,pi.invoice_number,pii.quantity,pii.unit_cost FROM purchase_invoice_items pii JOIN purchase_invoices pi ON pi.id=pii.purchase_invoice_id WHERE pii.product_id=:id ORDER BY pi.id DESC LIMIT 500",{"id":self.product_id})
        self._add_tab("المشتريات",["التاريخ","الفاتورة","الكمية","التكلفة"],[(x.get("invoice_date"),x.get("invoice_number"),x.get("quantity"),x.get("unit_cost")) for x in purchases])
        suppliers=self._query("SELECT s.name,ps.supplier_sku,ps.preferred FROM supplier_products ps JOIN suppliers s ON s.id=ps.supplier_id WHERE ps.product_id=:id ORDER BY s.name",{"id":self.product_id})
        self._add_tab("الموردون",["المورد","رمز المورد للصنف","مفضل"],[(x.get("name"),x.get("supplier_sku"),x.get("preferred")) for x in suppliers])
        self._add_tab("الملاحظات",["البيان","النص"],[("الوصف",product.get("description")),("الملاحظات",product.get("notes"))])

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
        self.search.textChanged.connect(lambda _: self.load())

        search_button = QPushButton("بحث")
        search_button.clicked.connect(self.load)

        add_button = QPushButton("إضافة صنف")
        add_button.clicked.connect(self.add_product)
        open_button = QPushButton("فتح بطاقة الصنف")
        open_button.clicked.connect(self.open_product_card)
        edit_button = QPushButton("تعديل الصنف")
        edit_button.clicked.connect(self.edit_product)
        delete_button = QPushButton("تعطيل/حذف الصنف")
        delete_button.clicked.connect(self.delete_product)
        bar.addWidget(add_button)
        bar.addWidget(open_button)
        bar.addWidget(edit_button)
        bar.addWidget(delete_button)

        refresh_button = QPushButton("تحديث")
        refresh_button.clicked.connect(lambda: self.load(""))

        bar.addWidget(self.search)
        bar.addWidget(search_button)
        bar.addWidget(refresh_button)
        layout.addLayout(bar)

        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels([
            "رقم", "الباركود", "رمز الصنف", "اسم المنتج", "التصنيف",
            "الوحدة", "التكلفة", "سعر البيع", "الكمية", "الحالة"
        ])
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.Stretch
        )
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(False)
        self.table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.doubleClicked.connect(lambda *_: self.open_product_card())
        layout.addWidget(self.table)

        self.status = QLabel("جاهز")
        self.status.setStyleSheet("padding:6px")
        layout.addWidget(self.status)

        self.load("")

    def open_product_card(self):
        row=self.table.currentRow()
        if row<0:
            QMessageBox.warning(self,"بطاقة الصنف","اختر صنفًا أولًا."); return
        try:
            dialog=ProductCardDialog(int(self.table.item(row,0).text()),self)
            dialog.exec()
        except Exception as exc:
            QMessageBox.critical(self,"فشل فتح بطاقة الصنف",str(exc))

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
        sku=QLineEdit(self.table.item(row,2).text())
        name=QLineEdit(self.table.item(row,3).text())
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
        cost.setValue(float(self.table.item(row,6).text() or 0)); sale.setValue(float(self.table.item(row,7).text() or 0))
        quantity.setValue(0)
        def load_selected_warehouse_quantity():
            try:
                from app.database.connection import get_session
                from sqlalchemy import text
                with get_session() as s:
                    current=s.execute(text("SELECT COALESCE(quantity,0) FROM stock_balances WHERE product_id=:p AND warehouse_id=:w"), {"p":product_id,"w":int(warehouse.currentData() or 1)}).scalar()
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
                    item.get("barcode", "") or "",
                    item.get("sku", "") or "",
                    item.get("name_ar", "") or "",
                    item.get("category_name", "") or "",
                    item.get("unit_name", "") or "",
                    item.get("cost_price", 0),
                    item.get("sale_price", 0),
                    item.get("quantity", 0),
                    "نشط",
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
