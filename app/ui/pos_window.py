from decimal import Decimal, ROUND_HALF_UP

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QLabel, QMessageBox,
    QHeaderView, QDialog, QFormLayout, QDoubleSpinBox, QDialogButtonBox,
    QComboBox, QInputDialog, QAbstractItemView
)
from app.services.party_service import PartyService
from app.services.pos_service import POSService
from app.services.tax_service import TaxService
from app.services.pos_hold_service import POSHoldService
from app.services.pos_search_service import POSProductSearch


class PaymentDialog(QDialog):
    """نافذة دفع موحدة تدعم الدفع المختلط والآجل مع اختيار العميل."""

    def __init__(self, total, parent=None):
        super().__init__(parent)
        self.total = Decimal(str(total)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        self.setWindowTitle("إتمام الدفع")
        self.setMinimumWidth(500)
        self.setLayoutDirection(Qt.RightToLeft)
        layout = QFormLayout(self)

        self.cash = self._money_box()
        self.card = self._money_box()
        self.transfer = self._money_box()
        self.credit = self._money_box()

        self.customer = QComboBox()
        self.customer.addItem("بدون عميل", None)
        try:
            for row in PartyService.customers():
                if row.get("is_active", 1):
                    self.customer.addItem(f'{row["id"]} - {row["name"]}', row["id"])
        except Exception:
            pass

        self.reference = QLineEdit()
        self.reference.setPlaceholderText("رقم العملية/المرجع - اختياري")
        self.total_label = QLabel(f"إجمالي الفاتورة: {self.total:.2f}")
        self.remaining_label = QLabel()
        layout.addRow("الإجمالي:", self.total_label)
        layout.addRow("نقدًا:", self.cash)
        layout.addRow("بطاقة:", self.card)
        layout.addRow("تحويل بنكي:", self.transfer)
        layout.addRow("آجل:", self.credit)
        layout.addRow("العميل:", self.customer)
        layout.addRow("مرجع الدفع:", self.reference)
        layout.addRow("المتبقي:", self.remaining_label)

        for widget in (self.cash, self.card, self.transfer, self.credit):
            widget.valueChanged.connect(self.update_remaining)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_if_valid)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        self.update_remaining()

    @staticmethod
    def _money_box():
        box = QDoubleSpinBox()
        box.setMaximum(999999999)
        box.setDecimals(2)
        return box

    def amounts(self):
        return {
            "cash": Decimal(str(self.cash.value())),
            "card": Decimal(str(self.card.value())),
            "bank_transfer": Decimal(str(self.transfer.value())),
            "credit": Decimal(str(self.credit.value())),
        }

    def update_remaining(self):
        paid = sum(self.amounts().values(), Decimal("0"))
        self.remaining_label.setText(f"{self.total - paid:.2f}")

    def accept_if_valid(self):
        amounts = self.amounts()
        total = sum(amounts.values(), Decimal("0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if total != self.total:
            QMessageBox.warning(
                self, "مجموع الدفعات غير صحيح",
                f"يجب أن يساوي مجموع الدفعات {self.total:.2f}.\nالمجموع الحالي: {total:.2f}"
            )
            return
        if amounts["credit"] > 0 and self.customer.currentData() is None:
            QMessageBox.warning(self, "العميل مطلوب", "اختر العميل عند وجود جزء آجل من الفاتورة.")
            return
        if total <= 0:
            QMessageBox.warning(self, "الدفع", "أدخل مبلغًا للدفع.")
            return
        super().accept()

    def payments(self):
        result = []
        for method, amount in self.amounts().items():
            if amount > 0:
                result.append({
                    "method": method,
                    "amount": float(amount),
                    "reference_number": self.reference.text().strip() or None,
                })
        return result

    def customer_id_value(self):
        return self.customer.currentData()


class ProductSelectionDialog(QDialog):
    """اختيار صنف متعدد النتائج بدل إضافة أول نتيجة بشكل صامت."""

    def __init__(self, products, parent=None):
        super().__init__(parent)
        self.setWindowTitle("اختيار الصنف")
        self.setMinimumSize(900, 480)
        self.setLayoutDirection(Qt.RightToLeft)
        self.selected_product = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("اختر الصنف ثم اضغط Enter أو انقر مرتين."))

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["المعرف", "الكود", "الصنف", "الباركود", "السعر", "المتاح"]
        )
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)

        for product in products:
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = [
                product.get("id"),
                product.get("sku") or "",
                product.get("name_ar") or product.get("name_en") or "",
                product.get("barcode") or "",
                f'{float(product.get("sale_price") or 0):.2f}',
                f'{float(product.get("available_quantity", product.get("stock", 0)) or 0):.2f}',
            ]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(str(value)))

        layout.addWidget(self.table)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_selection)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.table.itemDoubleClicked.connect(lambda *_: self.accept_selection())
        if self.table.rowCount():
            self.table.selectRow(0)
            self.table.setFocus()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.accept_selection()
            return
        super().keyPressEvent(event)

    def accept_selection(self):
        row = self.table.currentRow()
        if row < 0:
            return
        self.selected_product = self._products()[row]
        self.accept()

    def _products(self):
        return [
            {
                "id": self.table.item(row, 0).text(),
                "sku": self.table.item(row, 1).text(),
                "name_ar": self.table.item(row, 2).text(),
                "barcode": self.table.item(row, 3).text(),
                "sale_price": self.table.item(row, 4).text(),
                "available_quantity": self.table.item(row, 5).text(),
            }
            for row in range(self.table.rowCount())
        ]


class POSWindow(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cart = []
        self.search_engine = POSProductSearch()
        self._search_timer = None
        self._selected_suggestion = -1

        self.setWindowTitle("نقطة البيع")
        self.setMinimumSize(1200, 760)
        self.setLayoutDirection(Qt.RightToLeft)

        self.setStyleSheet("""
            QWidget { font-size:14px; }
            QTableWidget {
                background:#0D1B2A;
                color:#F4F7FB;
                gridline-color:#29435C;
                border:1px solid #29435C;
                border-radius:10px;
                selection-background-color:#244E72;
                selection-color:#FFFFFF;
            }
            QTableWidget::item { padding:8px; }
            QHeaderView::section {
                background:#13263D;
                color:#FFFFFF;
                padding:9px;
                border:0;
                border-bottom:1px solid #29435C;
                font-weight:700;
            }
            QLineEdit, QDoubleSpinBox {
                background:#0E1C2D;
                color:#FFFFFF;
                border:1px solid #29445F;
                border-radius:8px;
                padding:9px;
                min-height:22px;
            }
            QPushButton { padding:9px 14px; min-height:36px; }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("نقطة البيع")
        title.setStyleSheet("font-size:28px;font-weight:700;")
        header.addWidget(title)
        header.addStretch()
        self.search = QLineEdit()
        self.search.setPlaceholderText("ابحث عن صنف بالاسم أو الكود أو الباركود — النتائج تظهر أثناء الكتابة")
        self.search.setMinimumWidth(480)
        self.search.textChanged.connect(self.search_live)
        header.addWidget(self.search)
        root.addLayout(header)

        self.suggestions = QTableWidget(0, 5)
        self.suggestions.setHorizontalHeaderLabels(["الكود", "الصنف", "الباركود", "السعر", "المتاح"])
        self.suggestions.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.suggestions.horizontalHeader().resizeSection(0, 150)
        self.suggestions.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        for c in (2, 3, 4):
            self.suggestions.horizontalHeader().setSectionResizeMode(c, QHeaderView.Fixed)
            self.suggestions.horizontalHeader().resizeSection(c, 130)
        self.suggestions.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.suggestions.setSelectionMode(QAbstractItemView.SingleSelection)
        self.suggestions.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.suggestions.setAlternatingRowColors(True)
        self.suggestions.setMaximumHeight(210)
        self.suggestions.itemDoubleClicked.connect(lambda *_: self.add_selected_suggestion())

        root.addWidget(self.suggestions)

        entry = QHBoxLayout()
        self.code_entry = QLineEdit()
        self.code_entry.setPlaceholderText("أدخل الكود/الباركود هنا لإضافة مباشرة من القارئ")
        self.code_entry.returnPressed.connect(self.add_code_entry)
        entry.addWidget(self.code_entry, 1)
        root.addLayout(entry)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["الكود", "الصنف", "الكمية", "سعر الوحدة", "الخصم", "الإجمالي"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.resizeSection(0, 150)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        for c, width in ((2, 100), (3, 130), (4, 120), (5, 140)):
            header.setSectionResizeMode(c, QHeaderView.Fixed)
            header.resizeSection(c, width)

        self.table.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked | QAbstractItemView.EditKeyPressed)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setDefaultSectionSize(44)
        self.table.setTabKeyNavigation(True)
        self.table.itemChanged.connect(self._cell_changed)
        root.addWidget(self.table, 1)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("الكمية قابلة للتعديل مباشرة داخل الجدول"))
        controls.addStretch()
        remove = QPushButton("حذف الصف المحدد")
        remove.clicked.connect(self.remove_selected)
        controls.addWidget(remove)
        discount = QPushButton("تعديل خصم الصف")
        discount.clicked.connect(self.discount_selected)
        controls.addWidget(discount)
        root.addLayout(controls)

        totals = QHBoxLayout()
        self.subtotal_label = QLabel("قبل الضريبة: 0.00")
        self.discount_label = QLabel("الخصم: 0.00")
        self.taxable_label = QLabel("الخاضع للضريبة: 0.00")
        self.tax_label = QLabel("الضريبة: 0.00")
        self.total = QLabel("الإجمالي النهائي: 0.00")
        self.total.setStyleSheet("font-size:22px;font-weight:700;")
        for label in (self.subtotal_label, self.discount_label, self.taxable_label, self.tax_label, self.total):
            totals.addWidget(label)
        root.addLayout(totals)

        bottom = QHBoxLayout()
        bottom.addStretch()
        hold = QPushButton("تعليق")
        resume = QPushButton("استرجاع")
        clear = QPushButton("تفريغ")
        pay = QPushButton("إتمام البيع")
        hold.clicked.connect(self.hold_sale)
        resume.clicked.connect(self.resume_sale)
        clear.clicked.connect(self.clear_cart)
        pay.clicked.connect(self.complete_sale)
        bottom.addWidget(hold)
        bottom.addWidget(resume)
        bottom.addWidget(clear)
        bottom.addWidget(pay)
        root.addLayout(bottom)

        self.search.setFocus()

    def search_live(self, text):
        term = text.strip()
        self.suggestions.setRowCount(0)
        if not term:
            self._selected_suggestion = -1
            return

        try:
            products = self.search_engine.search(term)
        except Exception as exc:
            self.suggestions.setRowCount(0)
            return

        for product in products[:50]:
            row = self.suggestions.rowCount()
            self.suggestions.insertRow(row)
            values = [
                product.get("sku") or "",
                product.get("name_ar") or product.get("name_en") or "",
                product.get("barcode") or "",
                f'{float(product.get("sale_price") or 0):,.2f}',
                f'{float(product.get("available_quantity", product.get("stock", 0)) or 0):g}',
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter if column != 1 else Qt.AlignRight | Qt.AlignVCenter)
                self.suggestions.setItem(row, column, item)

        if self.suggestions.rowCount():
            self.suggestions.selectRow(0)
            self._selected_suggestion = 0

    def keyPressEvent(self, event):
        if self.suggestions.hasFocus():
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                self.add_selected_suggestion()
                return
            if event.key() == Qt.Key_Down:
                self._move_suggestion(1)
                return
            if event.key() == Qt.Key_Up:
                self._move_suggestion(-1)
                return
        super().keyPressEvent(event)

    def _move_suggestion(self, delta):
        count = self.suggestions.rowCount()
        if not count:
            return
        current = self.suggestions.currentRow()
        current = 0 if current < 0 else current
        target = max(0, min(count - 1, current + delta))
        self.suggestions.selectRow(target)
        self.suggestions.setFocus()

    def add_selected_suggestion(self):
        row = self.suggestions.currentRow()
        if row < 0:
            return
        sku = self.suggestions.item(row, 0).text()
        barcode = self.suggestions.item(row, 2).text()
        term = barcode or sku
        products = self.search_engine.search(term)
        if products:
            self._add_product(products[0])
        else:
            QMessageBox.warning(self, "الصنف", "تعذر إضافة الصنف المحدد.")
        self.search.setFocus()
        self.search.selectAll()

    def add_code_entry(self):
        term = self.code_entry.text().strip()
        if not term:
            return
        products = self.search_engine.search(term)
        if not products:
            QMessageBox.warning(self, "غير موجود", "لم يتم العثور على الصنف.")
            self.code_entry.selectAll()
            return
        self._add_product(products[0])
        self.code_entry.clear()
        self.search.setFocus()

    def _add_product(self, product):
        product_id = int(product["id"])
        for index, item in enumerate(self.cart):
            if item["product_id"] == product_id:
                item["quantity"] += 1
                self.refresh(select_index=index)
                self.search.setFocus()
                return

        self.cart.append({
            "product_id": product_id,
            "sku": product.get("sku") or "",
            "name": product.get("name_ar") or product.get("name_en") or "",
            "quantity": 1,
            "unit_price": float(product.get("sale_price") or 0),
            "discount": 0,
        })
        self.refresh(select_index=len(self.cart) - 1)
        self.search.setFocus()

    def selected_index(self):
        row = self.table.currentRow()
        return row if 0 <= row < len(self.cart) else None

    def _cell_changed(self, item):
        if getattr(self, "_loading_table", False):
            return
        row = item.row()
        if row < 0 or row >= len(self.cart) or item.column() != 2:
            return
        try:
            quantity = float(item.text().strip().replace(",", "."))
        except ValueError:
            QMessageBox.warning(self, "كمية غير صحيحة", "أدخل رقمًا صحيحًا للكمية.")
            self.refresh(select_index=row)
            return
        if quantity <= 0:
            self.cart.pop(row)
            self.refresh(select_index=max(0, row - 1))
            return
        self.cart[row]["quantity"] = quantity
        self.refresh(select_index=row)

    def _begin_edit(self, item):
        if item.column() == 2:
            self.table.editItem(item)

    def change_quantity(self, delta):
        index = self.selected_index()
        if index is None:
            return
        new_quantity = float(self.cart[index]["quantity"]) + delta
        if new_quantity <= 0:
            self.cart.pop(index)
        else:
            self.cart[index]["quantity"] = new_quantity
        self.refresh(select_index=max(0, index - 1))

    def remove_selected(self):
        index = self.selected_index()
        if index is not None:
            self.cart.pop(index)
            self.refresh(select_index=max(0, index - 1))

    def discount_selected(self):
        index = self.selected_index()
        if index is None:
            return
        item = self.cart[index]
        maximum = Decimal(str(item["quantity"])) * Decimal(str(item["unit_price"]))
        value, ok = QInputDialog.getDouble(
            self, "خصم الصف", "قيمة الخصم:", float(item["discount"]),
            0.0, float(maximum), 2
        )
        if ok:
            item["discount"] = value
            self.refresh(select_index=index)

    def refresh(self, select_index=None):
        self._loading_table = True
        self.table.setRowCount(0)
        subtotal = Decimal("0")
        discount_total = Decimal("0")
        taxable = Decimal("0")

        for item in self.cart:
            row = self.table.rowCount()
            self.table.insertRow(row)
            gross = Decimal(str(item["quantity"])) * Decimal(str(item["unit_price"]))
            discount = Decimal(str(item["discount"]))
            line = gross - discount
            subtotal += gross
            discount_total += discount
            taxable += line
            values = [
                item["sku"], item["name"], f'{float(item["quantity"]):g}',
                f'{item["unit_price"]:.2f}', f'{item["discount"]:.2f}', f'{line:.2f}'
            ]
            for column, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                cell.setTextAlignment(Qt.AlignCenter if column != 1 else Qt.AlignRight | Qt.AlignVCenter)
                if column != 2:
                    cell.setFlags(cell.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, column, cell)

        self._loading_table = False
        if self.cart:
            target = len(self.cart) - 1 if select_index is None else max(0, min(select_index, len(self.cart) - 1))
            self.table.setCurrentCell(target, 2)
        subtotal = subtotal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        discount_total = discount_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        taxable = taxable.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        tax_data = TaxService.calculate(taxable)
        grand = Decimal(str(tax_data["total"]))
        self.subtotal_label.setText(f"قبل الضريبة: {subtotal:.2f}")
        self.discount_label.setText(f"الخصم: {discount_total:.2f}")
        self.taxable_label.setText(f"الخاضع للضريبة: {taxable:.2f}")
        self.tax_label.setText(f"ضريبة القيمة المضافة ({tax_data['rate'] * 100:.2f}%): {tax_data['tax']:.2f}")
        self.total.setText(f"الإجمالي النهائي: {grand:.2f}")

    def current_total(self):
        return Decimal(str(self.total.text().split(":")[-1].strip()))

    def complete_sale(self):
        if not self.cart:
            QMessageBox.warning(self, "تنبيه", "الفاتورة فارغة.")
            return
        dialog = PaymentDialog(self.current_total(), self)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            result = POSService.create_sale(
                self.cart,
                payment_method=dialog.payments()[0]["method"],
                payments=dialog.payments(),
                customer_id=dialog.customer_id_value(),
            )
            QMessageBox.information(
                self, "تمت العملية",
                f"تم إنشاء الفاتورة\\n{result['invoice_number']}\\nالإجمالي: {result['total']:.2f}"
            )
            self.cart = []
            self.refresh()
            self.search.setFocus()
        except Exception as exc:
            QMessageBox.critical(self, "فشل البيع", str(exc))

    def hold_sale(self):
        if not self.cart:
            return
        import copy
        try:
            result = POSHoldService.hold(copy.deepcopy(self.cart), "cash", "تعليق من نقطة البيع")
            self.clear_cart()
            QMessageBox.information(self, "تم التعليق", f"تم حفظ الفاتورة المعلقة برقم {result['hold_number']}")
        except Exception as exc:
            QMessageBox.critical(self, "فشل التعليق", str(exc))

    def resume_sale(self):
        try:
            rows = POSHoldService.list_held()
            if not rows:
                QMessageBox.information(self, "الفواتير المعلقة", "لا توجد فاتورة معلقة محفوظة.")
                return
            labels = [f"{r['hold_number']} | {r.get('notes') or 'بدون ملاحظات'}" for r in rows]
            selected, ok = QInputDialog.getItem(self, "استرجاع فاتورة معلقة", "اختر الفاتورة:", labels, 0, False)
            if not ok:
                return
            result = POSHoldService.resume(rows[labels.index(selected)]["id"])
            self.cart = result["items"]
            self.refresh()
            self.search.setFocus()
        except Exception as exc:
            QMessageBox.critical(self, "فشل الاسترجاع", str(exc))

    def clear_cart(self):
        self.cart = []
        self.refresh()
        self.search.setFocus()
