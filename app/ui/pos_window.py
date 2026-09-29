from decimal import Decimal, ROUND_HALF_UP

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QLabel, QMessageBox,
    QHeaderView, QDialog, QFormLayout, QDoubleSpinBox, QDialogButtonBox,
    QComboBox, QSpinBox, QInputDialog
)
from app.services.inventory_service import InventoryService
from app.services.party_service import PartyService
from app.services.pos_service import POSService
from app.services.tax_service import TaxService


class PaymentDialog(QDialog):
    """نافذة دفع موحدة تدعم الدفع المختلط والآجل مع اختيار العميل."""

    def __init__(self, total, parent=None):
        super().__init__(parent)
        self.total = Decimal(str(total)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
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
                    label = f'{row["id"]} - {row["name"]}'
                    self.customer.addItem(label, row["id"])
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

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
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
        remaining = self.total - paid
        self.remaining_label.setText(f"{remaining:.2f}")

    def accept_if_valid(self):
        amounts = self.amounts()
        total = sum(amounts.values(), Decimal("0")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if total != self.total:
            QMessageBox.warning(
                self, "مجموع الدفعات غير صحيح",
                f"يجب أن يساوي مجموع الدفعات {self.total:.2f}.\n"
                f"المجموع الحالي: {total:.2f}"
            )
            return
        if amounts["credit"] > 0 and self.customer.currentData() is None:
            QMessageBox.warning(
                self, "العميل مطلوب",
                "اختر العميل عند وجود جزء آجل من الفاتورة."
            )
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


class POSWindow(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cart = []
        self.setWindowTitle("نقطة البيع")
        self.setMinimumSize(1100, 650)

        layout = QVBoxLayout(self)

        title = QLabel("نقطة البيع")
        title.setStyleSheet("font-size:28px;font-weight:bold")
        layout.addWidget(title)

        top = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(
            "باركود / رمز الصنف / اسم المنتج ثم Enter"
        )
        self.search.returnPressed.connect(self.add_search_result)

        add = QPushButton("إضافة")
        add.clicked.connect(self.add_search_result)
        top.addWidget(self.search)
        top.addWidget(add)
        layout.addLayout(top)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["الصنف", "الكمية", "السعر", "الخصم", "الإجمالي"]
        )
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

        controls = QHBoxLayout()
        plus = QPushButton("زيادة الكمية")
        minus = QPushButton("إنقاص الكمية")
        remove = QPushButton("حذف الصنف")
        discount = QPushButton("خصم السطر")
        plus.clicked.connect(lambda: self.change_quantity(1))
        minus.clicked.connect(lambda: self.change_quantity(-1))
        remove.clicked.connect(self.remove_selected)
        discount.clicked.connect(self.discount_selected)
        controls.addWidget(plus)
        controls.addWidget(minus)
        controls.addWidget(remove)
        controls.addWidget(discount)
        controls.addStretch()
        layout.addLayout(controls)

        bottom = QHBoxLayout()
        self.total = QLabel("الإجمالي مع الضريبة: 0.00")
        self.total.setStyleSheet("font-size:22px;font-weight:bold")
        pay = QPushButton("الدفع وإتمام البيع")
        clear = QPushButton("تفريغ الفاتورة")
        pay.clicked.connect(self.complete_sale)
        clear.clicked.connect(self.clear_cart)
        bottom.addWidget(self.total)
        bottom.addStretch()
        bottom.addWidget(clear)
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

    def add_search_result(self):
        term = self.search.text().strip()
        if not term:
            return
        products = InventoryService.search_products(term)
        if not products:
            QMessageBox.warning(self, "غير موجود", "لم يتم العثور على الصنف")
            return
        product = products[0]
        for item in self.cart:
            if item["product_id"] == product["id"]:
                item["quantity"] += 1
                self.refresh()
                self.search.clear()
                return
        self.cart.append({
            "product_id": product["id"],
            "name": product["name_ar"],
            "quantity": 1,
            "unit_price": float(product["sale_price"]),
            "discount": 0,
        })
        self.refresh()
        self.search.clear()

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
            f"الخصم للصنف: {item['name']} (الحد الأقصى {maximum:.2f})",
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
        for item in self.cart:
            row = self.table.rowCount()
            self.table.insertRow(row)
            line = (
                Decimal(str(item["quantity"])) *
                Decimal(str(item["unit_price"])) -
                Decimal(str(item["discount"]))
            )
            subtotal += line
            values = [
                item["name"], item["quantity"],
                f'{item["unit_price"]:.2f}',
                f'{item["discount"]:.2f}',
                f'{line:.2f}',
            ]
            for column, value in enumerate(values):
                self.table.setItem(
                    row, column, QTableWidgetItem(str(value))
                )
        tax_data = TaxService.calculate(subtotal)
        grand = Decimal(str(tax_data["total"]))
        self.total.setText(f"الإجمالي مع الضريبة: {grand:.2f}")

    def current_total(self):
        return Decimal(self.total.text().split(":")[-1].strip())

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
                f"تم إنشاء الفاتورة\\n{result['invoice_number']}\\n"
                f"الإجمالي: {result['total']:.2f}\\n"
                f"المدفوع: {result['paid']:.2f}\\n"
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
        if not hasattr(self, "held_sales"):
            self.held_sales = []
        self.held_sales.append(copy.deepcopy(self.cart))
        self.clear_cart()
        QMessageBox.information(self, "تم التعليق", f"تم تعليق الفاتورة رقم {len(self.held_sales)}")

    def resume_sale(self):
        if not getattr(self, "held_sales", None):
            QMessageBox.information(self, "الفواتير المعلقة", "لا توجد فاتورة معلقة")
            return
        self.cart = self.held_sales.pop()
        self.refresh()
        self.search.setFocus()

    def clear_cart(self):
        self.cart = []
        self.refresh()
        self.search.setFocus()
