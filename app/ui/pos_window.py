from decimal import Decimal, ROUND_HALF_UP

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QLabel, QMessageBox,
    QHeaderView, QDialog, QFormLayout, QDoubleSpinBox, QDialogButtonBox,
    QSpinBox
)
from app.services.inventory_service import InventoryService
from app.services.pos_service import POSService


class PaymentDialog(QDialog):
    """نافذة دفع موحدة تدعم الدفع المختلط والآجل."""

    def __init__(self, total, parent=None):
        super().__init__(parent)
        self.total = Decimal(str(total)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        self.setWindowTitle("إتمام الدفع")
        self.setMinimumWidth(420)

        layout = QFormLayout(self)

        self.cash = QDoubleSpinBox()
        self.cash.setMaximum(999999999)
        self.cash.setDecimals(2)

        self.card = QDoubleSpinBox()
        self.card.setMaximum(999999999)
        self.card.setDecimals(2)

        self.transfer = QDoubleSpinBox()
        self.transfer.setMaximum(999999999)
        self.transfer.setDecimals(2)

        self.credit = QDoubleSpinBox()
        self.credit.setMaximum(999999999)
        self.credit.setDecimals(2)

        self.customer_id = QSpinBox()
        self.customer_id.setMinimum(0)
        self.customer_id.setMaximum(999999999)
        self.customer_id.setSpecialValueText("بدون عميل")

        self.reference = QLineEdit()
        self.reference.setPlaceholderText("رقم العملية/المرجع - اختياري")

        self.total_label = QLabel(f"إجمالي الفاتورة: {self.total:.2f}")
        self.remaining_label = QLabel()

        layout.addRow("الإجمالي:", self.total_label)
        layout.addRow("نقدًا:", self.cash)
        layout.addRow("بطاقة:", self.card)
        layout.addRow("تحويل بنكي:", self.transfer)
        layout.addRow("آجل:", self.credit)
        layout.addRow("رقم العميل عند البيع الآجل:", self.customer_id)
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
                self,
                "مجموع الدفعات غير صحيح",
                f"يجب أن يساوي مجموع الدفعات {self.total:.2f}.\n"
                f"المجموع الحالي: {total:.2f}"
            )
            return

        if amounts["credit"] > 0 and self.customer_id.value() <= 0:
            QMessageBox.warning(
                self,
                "العميل مطلوب",
                "لا يمكن تسجيل الجزء الآجل بدون رقم عميل."
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
        return self.customer_id.value() or None


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
            "ابحث بالباركود أو رمز الصنف أو اسم المنتج..."
        )
        self.search.returnPressed.connect(self.add_search_result)

        add = QPushButton("إضافة")
        add.clicked.connect(self.add_search_result)

        top.addWidget(self.search)
        top.addWidget(add)
        layout.addLayout(top)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            "الصنف", "الكمية", "السعر", "الخصم", "الإجمالي"
        ])
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

        bottom = QHBoxLayout()

        self.total = QLabel("الإجمالي مع الضريبة: 0.00")
        self.total.setStyleSheet("font-size:22px;font-weight:bold")

        pay = QPushButton("الدفع وإتمام البيع")
        pay.clicked.connect(self.complete_sale)

        clear = QPushButton("تفريغ الفاتورة")
        clear.clicked.connect(self.clear_cart)

        bottom.addWidget(self.total)
        bottom.addStretch()
        bottom.addWidget(clear)
        bottom.addWidget(pay)
        layout.addLayout(bottom)

    def add_search_result(self):
        term = self.search.text().strip()
        if not term:
            return

        products = InventoryService.search_products(term)
        if not products:
            QMessageBox.warning(
                self, "غير موجود", "لم يتم العثور على الصنف"
            )
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

    def refresh(self):
        self.table.setRowCount(0)
        subtotal = Decimal("0")

        for item in self.cart:
            row = self.table.rowCount()
            self.table.insertRow(row)

            line = (
                Decimal(str(item["quantity"])) *
                Decimal(str(item["unit_price"]))
            ) - Decimal(str(item["discount"]))

            subtotal += line

            values = [
                item["name"],
                item["quantity"],
                f'{item["unit_price"]:.2f}',
                f'{item["discount"]:.2f}',
                f'{line:.2f}',
            ]

            for column, value in enumerate(values):
                self.table.setItem(
                    row, column, QTableWidgetItem(str(value))
                )

        tax = (subtotal * Decimal("0.15")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        grand = (subtotal + tax).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        self.total.setText(
            f"الإجمالي مع الضريبة: {grand:.2f}"
        )

    def current_total(self):
        text = self.total.text().split(":")[-1].strip()
        return Decimal(text)

    def complete_sale(self):
        if not self.cart:
            QMessageBox.warning(
                self, "تنبيه", "الفاتورة فارغة"
            )
            return

        total = self.current_total()
        dialog = PaymentDialog(total, self)

        if dialog.exec() != QDialog.Accepted:
            return

        payments = dialog.payments()
        customer_id = dialog.customer_id_value()

        try:
            result = POSService.create_sale(
                self.cart,
                payment_method=payments[0]["method"],
                payments=payments,
                customer_id=customer_id,
            )

            QMessageBox.information(
                self,
                "تمت العملية",
                f"تم إنشاء الفاتورة\n"
                f"{result['invoice_number']}\n"
                f"الإجمالي: {result['total']:.2f}\n"
                f"المدفوع: {result['paid']:.2f}\n"
                f"الآجل: {result['due']:.2f}"
            )

            self.cart = []
            self.refresh()

        except Exception as exc:
            QMessageBox.critical(
                self,
                "فشل البيع",
                str(exc)
            )

    def clear_cart(self):
        self.cart = []
        self.refresh()
