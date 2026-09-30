from decimal import Decimal, ROUND_HALF_UP

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QLabel, QMessageBox,
    QHeaderView, QDialog, QFormLayout, QDoubleSpinBox, QDialogButtonBox,
    QComboBox, QInputDialog, QAbstractItemView
)
from app.services.inventory_service import InventoryService
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
        self.setMinimumSize(850, 420)
        self.selected_product = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("اختر الصنف المطلوب ثم اضغط Enter أو انقر مرتين."))

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["المعرف", "الكود", "الصنف", "الباركود", "السعر", "المتاح"]
        )
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)

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
        self.setWindowTitle("نقطة البيع")
        self.setMinimumSize(1100, 650)
        layout = QVBoxLayout(self)

        title = QLabel("نقطة البيع")
        title.setStyleSheet("font-size:28px;font-weight:bold")
        layout.addWidget(title)

        top = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("باركود / رمز الصنف / اسم المنتج ثم Enter")
        self.search.returnPressed.connect(self.add_search_result)
        add = QPushButton("إضافة")
        add.clicked.connect(self.add_search_result)
        top.addWidget(self.search)
        top.addWidget(add)
        layout.addLayout(top)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["الصنف", "الكمية", "السعر", "الخصم", "الإجمالي"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

        controls = QHBoxLayout()
        for label, handler in (
            ("زيادة الكمية", lambda: self.change_quantity(1)),
            ("إنقاص الكمية", lambda: self.change_quantity(-1)),
            ("حذف الصنف", self.remove_selected),
            ("خصم السطر", self.discount_selected),
        ):
            button = QPushButton(label)
            button.clicked.connect(handler)
            controls.addWidget(button)
        controls.addStretch()
        layout.addLayout(controls)

        totals = QHBoxLayout()
        self.subtotal_label = QLabel("قبل الضريبة: 0.00")
        self.discount_label = QLabel("الخصم: 0.00")
        self.taxable_label = QLabel("الخاضع للضريبة: 0.00")
        self.tax_label = QLabel("ضريبة القيمة المضافة: 0.00")
        self.total = QLabel("الإجمالي النهائي: 0.00")
        self.total.setStyleSheet("font-size:22px;font-weight:bold")
        for label in (self.subtotal_label, self.discount_label, self.taxable_label, self.tax_label, self.total):
            totals.addWidget(label)
        layout.addLayout(totals)

        bottom = QHBoxLayout()
        pay = QPushButton("الدفع وإتمام البيع")
        clear = QPushButton("تفريغ الفاتورة")
        pay.clicked.connect(self.complete_sale)
        clear.clicked.connect(self.clear_cart)
        bottom.addWidget(clear)
        bottom.addStretch()
        bottom.addWidget(pay)
        layout.addLayout(bottom)

        self._setup_shortcuts()
        self.search.setFocus()

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("F1"), self, activated=self.search.setFocus)
        QShortcut(QKeySequence("F2"), self, activated=self.complete_sale)
        QShortcut(QKeySequence("F3"), self, activated=lambda: self.change_quantity(1))
        QShortcut(QKeySequence("F4"), self, activated=self.clear_cart)
        QShortcut(QKeySequence("F5"), self, activated=lambda: self.change_quantity(-1))
        QShortcut(QKeySequence("F6"), self, activated=self.remove_selected)
        QShortcut(QKeySequence("F7"), self, activated=self.discount_selected)
        QShortcut(QKeySequence("F8"), self, activated=self.hold_sale)
        QShortcut(QKeySequence("F9"), self, activated=self.resume_sale)
        QShortcut(QKeySequence("Delete"), self, activated=self.remove_selected)
        QShortcut(QKeySequence("Escape"), self, activated=self.search.setFocus)

    def _add_product(self, product):
        product_id = int(product["id"])
        for item in self.cart:
            if item["product_id"] == product_id:
                item["quantity"] += 1
                self.refresh()
                self.search.clear()
                self.search.setFocus()
                return
        self.cart.append({
            "product_id": product_id,
            "name": product.get("name_ar") or product.get("name_en") or "",
            "quantity": 1,
            "unit_price": float(product.get("sale_price") or 0),
            "discount": 0,
        })
        self.refresh()
        self.search.clear()
        self.search.setFocus()

    def add_search_result(self):
        term = self.search.text().strip()
        if not term:
            return
        products = self.search_engine.search(term)
        if not products:
            QMessageBox.warning(self, "غير موجود", "لم يتم العثور على الصنف")
            return

        exact = [
            p for p in products
            if term == str(p.get("barcode") or "")
            or term == str(p.get("sku") or "")
            or term == str(p.get("id") or "")
        ]
        if len(exact) == 1:
            self._add_product(exact[0])
            return

        if len(products) == 1:
            self._add_product(products[0])
            return

        dialog = ProductSelectionDialog(products, self)
        if dialog.exec() == QDialog.Accepted and dialog.selected_product:
            self._add_product(dialog.selected_product)

    def selected_index(self):
        row = self.table.currentRow()
        return row if 0 <= row < len(self.cart) else None

    def change_quantity(self, delta):
        index = self.selected_index()
        if index is None:
            return
        new_quantity = self.cart[index]["quantity"] + delta
        if new_quantity <= 0:
            self.cart.pop(index)
        else:
            self.cart[index]["quantity"] = new_quantity
        self.refresh()

    def remove_selected(self):
        index = self.selected_index()
        if index is not None:
            self.cart.pop(index)
            self.refresh()

    def discount_selected(self):
        index = self.selected_index()
        if index is None:
            QMessageBox.warning(self, "الخصم", "اختر صنفًا أولاً")
            return
        item = self.cart[index]
        maximum = Decimal(str(item["quantity"])) * Decimal(str(item["unit_price"]))
        value, ok = QInputDialog.getDouble(
            self,
            "خصم السطر",
            f'الخصم للصنف: {item["name"]} (الحد الأقصى {maximum:.2f})',
            float(item["discount"]),
            0.0,
            float(maximum),
            2,
        )
        if ok:
            item["discount"] = value
            self.refresh()

    def refresh(self):
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
                item["name"], item["quantity"], f'{item["unit_price"]:.2f}',
                f'{item["discount"]:.2f}', f'{line:.2f}',
            ]
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))

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
            QMessageBox.warning(self, "تنبيه", "الفاتورة فارغة")
            return
        dialog = PaymentDialog(self.current_total(), self)
        if dialog.exec() != QDialog.Accepted:
            return
        payments = dialog.payments()
        try:
            result = POSService.create_sale(
                self.cart,
                payment_method=payments[0]["method"],
                payments=payments,
                customer_id=dialog.customer_id_value(),
            )
            QMessageBox.information(
                self, "تمت العملية",
                f"تم إنشاء الفاتورة\n{result['invoice_number']}\n"
                f"الإجمالي: {result['total']:.2f}\n"
                f"المدفوع: {result['paid']:.2f}\n"
                f"الآجل: {result['due']:.2f}"
            )
            self.cart = []
            self.refresh()
            self.search.setFocus()
        except Exception as exc:
            QMessageBox.critical(self, "فشل البيع", str(exc))

    def hold_sale(self):
        if not self.cart:
            QMessageBox.warning(self, "تعليق", "الفاتورة فارغة")
            return
        import copy
        try:
            result = POSHoldService.hold(
                items=copy.deepcopy(self.cart),
                payment_method="cash",
                notes="تعليق من نقطة البيع",
            )
            self.clear_cart()
            QMessageBox.information(self, "تم التعليق", f"تم حفظ الفاتورة المعلقة برقم {result['hold_number']}")
        except Exception as exc:
            QMessageBox.critical(self, "فشل التعليق", str(exc))

    def resume_sale(self):
        try:
            rows = POSHoldService.list_held()
            if not rows:
                QMessageBox.information(self, "الفواتير المعلقة", "لا توجد فاتورة معلقة محفوظة")
                return
            labels = [f"{r['hold_number']} | {r.get('notes') or 'بدون ملاحظات'}" for r in rows]
            selected, ok = QInputDialog.getItem(self, "استرجاع فاتورة معلقة", "اختر الفاتورة:", labels, 0, False)
            if not ok:
                return
            idx = labels.index(selected)
            result = POSHoldService.resume(rows[idx]["id"])
            self.cart = result["items"]
            self.refresh()
            self.search.setFocus()
        except Exception as exc:
            QMessageBox.critical(self, "فشل الاسترجاع", str(exc))

    def clear_cart(self):
        self.cart = []
        self.refresh()
        self.search.setFocus()
