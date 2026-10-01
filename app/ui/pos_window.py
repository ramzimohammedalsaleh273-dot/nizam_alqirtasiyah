from decimal import Decimal, ROUND_HALF_UP

from PySide6.QtCore import Qt, QTimer
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
from app.ui.theme import APP_STYLE


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
            QMessageBox.warning(self, "مجموع الدفعات غير صحيح",
                                f"يجب أن يساوي مجموع الدفعات {self.total:.2f}.\nالمجموع الحالي: {total:.2f}")
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


class POSWindow(QWidget):
    """نقطة بيع بجدول إدخال أصناف شبيه بجدول Access/Excel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cart = []
        self.search_engine = POSProductSearch()
        self._loading_table = False
        self._editing_product_cell = False
        self._product_edit_timer = None

        self.setWindowTitle("نقطة البيع")
        self.setMinimumSize(1250, 780)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setStyleSheet(APP_STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        title_row = QHBoxLayout()
        title = QLabel("نقطة البيع")
        title.setStyleSheet("font-size:28px;font-weight:700;")
        title_row.addWidget(title)
        title_row.addStretch()
        root.addLayout(title_row)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("بحث لحظي:"))
        self.search = QLineEdit()
        self.search.setPlaceholderText("اكتب أول حرف أو رقم وستظهر النتائج فورًا")
        self.search.setMinimumHeight(42)
        self.search.textChanged.connect(self.search_live)
        search_row.addWidget(self.search, 1)
        root.addLayout(search_row)

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
        self.suggestions.setMaximumHeight(190)
        self.suggestions.itemDoubleClicked.connect(lambda *_: self.add_selected_suggestion())
        root.addWidget(self.suggestions)

        # الجدول الرئيسي: هو مكان إدخال الفاتورة نفسه.
        self.table = QTableWidget(1, 10)
        self.table.setHorizontalHeaderLabels([
            "م", "الباركود / الإدخال", "كود الصنف", "اسم الصنف", "الوحدة",
            "الكمية", "السعر", "الخصم", "الضريبة", "الإجمالي"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.resizeSection(0, 55)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.resizeSection(1, 180)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.resizeSection(2, 120)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        for c, width in ((4, 85), (5, 85), (6, 105), (7, 95), (8, 100), (9, 125)):
            header.setSectionResizeMode(c, QHeaderView.Fixed)
            header.resizeSection(c, width)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(
            QAbstractItemView.DoubleClicked |
            QAbstractItemView.SelectedClicked |
            QAbstractItemView.EditKeyPressed
        )
        self.table.itemChanged.connect(self._cell_changed)
        self.table.cellDoubleClicked.connect(self._cell_double_clicked)
        root.addWidget(self.table, 1)

        hint = QLabel("أدخل الصنف في الخلية الأولى للصف. بعد التعرف عليه يُملأ الصف تلقائيًا ويُنشأ صف جديد تحته مباشرة.")
        hint.setStyleSheet("color:#9FB3C8;padding:3px;")
        root.addWidget(hint)

        controls = QHBoxLayout()
        remove = QPushButton("حذف الصف المحدد")
        remove.clicked.connect(self.remove_selected)
        discount = QPushButton("تعديل خصم الصف")
        discount.clicked.connect(self.discount_selected)
        controls.addWidget(remove)
        controls.addWidget(discount)
        controls.addStretch()
        root.addLayout(controls)

        totals = QHBoxLayout()
        self.subtotal_label = QLabel("قبل الضريبة: 0.00")
        self.discount_label = QLabel("الخصم: 0.00")
        self.tax_label = QLabel("الضريبة: 0.00")
        self.total = QLabel("الإجمالي النهائي: 0.00")
        self.total.setStyleSheet("font-size:22px;font-weight:700;")
        for label in (self.subtotal_label, self.discount_label, self.tax_label, self.total):
            totals.addWidget(label)
        totals.addStretch()
        root.addLayout(totals)

        bottom = QHBoxLayout()
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
        bottom.addStretch()
        bottom.addWidget(pay)
        root.addLayout(bottom)

        self._ensure_blank_row()
        self._focus_product_cell(0)
        self._shortcuts = []
        for key, slot in [
            ("F1", lambda: self.search.setFocus()),
            ("F2", self.clear_cart),
            ("F3", lambda: self.search.selectAll()),
            ("F4", self.hold_sale),
            ("F5", self.resume_sale),
            ("F6", self.complete_sale),
            ("F7", self.remove_selected),
            ("F8", self.discount_selected),
            ("F9", self.complete_sale),
            ("Esc", lambda: self.search.clearFocus()),
        ]:
            sc = QShortcut(QKeySequence(key), self)
            sc.activated.connect(slot)
            self._shortcuts.append(sc)

    def _product_cell(self, row):
        return self.table.item(row, 1)

    def _ensure_blank_row(self):
        if self.table.rowCount() == 0:
            self.table.insertRow(0)
        last = self.table.rowCount() - 1
        if self._product_cell(last) is None:
            self._loading_table = True
            self.table.setItem(last, 1, QTableWidgetItem(""))
            self._loading_table = False
        self.table.setItem(last, 0, QTableWidgetItem(str(last + 1)))
        for col in range(2, 10):
            if self.table.item(last, col) is None:
                self.table.setItem(last, col, QTableWidgetItem(""))

    def _focus_product_cell(self, row):
        row = max(0, min(row, self.table.rowCount() - 1))
        self.table.setCurrentCell(row, 1)
        self.table.editItem(self.table.item(row, 1))

    def search_live(self, text):
        term = text.strip()
        self.suggestions.setRowCount(0)
        if not term:
            return
        try:
            products = self.search_engine.search(term)
        except Exception:
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
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter if col != 1 else Qt.AlignRight | Qt.AlignVCenter)
                self.suggestions.setItem(row, col, item)
        if self.suggestions.rowCount():
            self.suggestions.selectRow(0)

    def add_selected_suggestion(self):
        row = self.suggestions.currentRow()
        if row < 0:
            return
        term = self.suggestions.item(row, 2).text() or self.suggestions.item(row, 0).text()
        products = self.search_engine.search(term)
        if products:
            self._add_product_to_cart(products[0])
        self.search.setFocus()
        self.search.selectAll()

    def _cell_changed(self, item):
        if self._loading_table:
            return
        row, col = item.row(), item.column()
        if row < 0:
            return

        if col == 1:
            text = item.text().strip()
            if not text:
                return
            # لا نبحث مع كل حرف داخل خلية الإدخال؛ ننتظر توقفًا قصيرًا
            # حتى يعمل قارئ الباركود والكتابة اليدوية دون واجهة اقتراحات.
            if self._product_edit_timer:
                self._product_edit_timer.stop()
            self._product_edit_timer = QTimer(self)
            self._product_edit_timer.setSingleShot(True)
            self._product_edit_timer.timeout.connect(
                lambda r=row, value=text: self._resolve_product_cell(r, value)
            )
            self._product_edit_timer.start(250)
            return

        if col == 5 and row < len(self.cart):
            try:
                quantity = float(item.text().strip().replace(",", "."))
                if quantity <= 0:
                    raise ValueError
                self.cart[row]["quantity"] = quantity
                self.refresh()
            except ValueError:
                QMessageBox.warning(self, "كمية غير صحيحة", "أدخل رقمًا صحيحًا للكمية.")
                self.refresh()

    def _cell_double_clicked(self, row, col):
        if col == 1:
            self.table.editItem(self.table.item(row, 1))
        elif col == 5 and row < len(self.cart):
            self.table.editItem(self.table.item(row, 5))

    def _resolve_product_cell(self, row, value):
        if row >= self.table.rowCount():
            return
        products = self.search_engine.search(value)
        exact = [
            p for p in products
            if str(p.get("sku") or "") == value
            or str(p.get("barcode") or "") == value
            or str(p.get("id") or "") == value
        ]
        if not exact:
            if len(products) == 1:
                exact = products
            else:
                self.table.item(row, 1).setText(value)
                return
        self._add_product_to_cart(exact[0], target_row=row)

    def _add_product_to_cart(self, product, target_row=None):
        product_id = int(product["id"])
        existing = next((i for i, x in enumerate(self.cart) if x["product_id"] == product_id), None)

        if existing is not None and target_row != existing:
            self.cart[existing]["quantity"] += 1
            self.refresh()
            self._focus_product_cell(len(self.cart))
            return

        if target_row is None:
            target_row = len(self.cart)

        if target_row < len(self.cart):
            self.cart[target_row]["quantity"] += 1
        else:
            self.cart.append({
                "product_id": product_id,
                "sku": product.get("sku") or "",
                "name": product.get("name_ar") or product.get("name_en") or "",
                "barcode": product.get("barcode") or "",
                "unit": product.get("unit_name") or product.get("unit") or "—",
                "quantity": 1,
                "unit_price": float(product.get("sale_price") or 0),
                "discount": 0,
            })
        self.refresh()
        self._focus_product_cell(len(self.cart))

    def selected_index(self):
        row = self.table.currentRow()
        return row if 0 <= row < len(self.cart) else None

    def refresh(self):
        self._loading_table = True
        self.table.setRowCount(len(self.cart) + 1)
        subtotal = Decimal("0")
        discount_total = Decimal("0")
        taxable = Decimal("0")

        for row, item in enumerate(self.cart):
            gross = Decimal(str(item["quantity"])) * Decimal(str(item["unit_price"]))
            discount = Decimal(str(item["discount"]))
            line = gross - discount
            tax_data = TaxService.calculate(line)
            subtotal += gross
            discount_total += discount
            taxable += line

            values = [
                str(row + 1), item.get("barcode") or item.get("sku") or "",
                item.get("sku") or "", item["name"], item.get("unit") or "—",
                f'{float(item["quantity"]):g}', f'{item["unit_price"]:.2f}',
                f'{item["discount"]:.2f}', f'{float(tax_data["tax"]):.2f}',
                f'{float(tax_data["total"]):.2f}'
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setTextAlignment(Qt.AlignCenter if col != 1 else Qt.AlignRight | Qt.AlignVCenter)
                if col not in (1, 5):
                    cell.setFlags(cell.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, col, cell)

        blank = len(self.cart)
        self.table.setItem(blank, 0, QTableWidgetItem(str(blank + 1)))
        self.table.setItem(blank, 1, QTableWidgetItem(""))
        for col in range(2, 10):
            self.table.setItem(blank, col, QTableWidgetItem(""))

        self._loading_table = False

        tax_data = TaxService.calculate(taxable)
        grand = Decimal(str(tax_data["total"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        self.subtotal_label.setText(f"قبل الضريبة: {subtotal.quantize(Decimal('0.01')):.2f}")
        self.discount_label.setText(f"الخصم: {discount_total.quantize(Decimal('0.01')):.2f}")
        self.tax_label.setText(f"الضريبة ({tax_data['rate'] * 100:.2f}%): {tax_data['tax']:.2f}")
        self.total.setText(f"الإجمالي النهائي: {grand:.2f}")

    def current_total(self):
        return Decimal(str(self.total.text().split(":")[-1].strip()))

    def remove_selected(self):
        index = self.selected_index()
        if index is not None:
            self.cart.pop(index)
            self.refresh()
            self._focus_product_cell(min(index, len(self.cart)))

    def discount_selected(self):
        index = self.selected_index()
        if index is None:
            return
        item = self.cart[index]
        maximum = Decimal(str(item["quantity"])) * Decimal(str(item["unit_price"]))
        value, ok = QInputDialog.getDouble(
            self, "خصم الصف", "قيمة الخصم:", float(item["discount"]), 0.0, float(maximum), 2
        )
        if ok:
            item["discount"] = value
            self.refresh()
            self._focus_product_cell(index)

    def complete_sale(self):
        if not self.cart:
            QMessageBox.warning(self, "تنبيه", "الفاتورة فارغة.")
            return
        dialog = PaymentDialog(self.current_total(), self)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            payments = dialog.payments()
            result = POSService.create_sale(
                self.cart,
                payment_method=payments[0]["method"],
                payments=payments,
                customer_id=dialog.customer_id_value(),
            )
            QMessageBox.information(self, "تمت العملية",
                                    f"تم إنشاء الفاتورة\n{result['invoice_number']}\nالإجمالي: {result['total']:.2f}")
            self.cart = []
            self.refresh()
            self._focus_product_cell(0)
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
            self._focus_product_cell(len(self.cart))
        except Exception as exc:
            QMessageBox.critical(self, "فشل الاسترجاع", str(exc))

    def clear_cart(self):
        self.cart = []
        self.refresh()
        self._focus_product_cell(0)
