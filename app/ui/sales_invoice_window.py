from PySide6.QtCore import Qt
from PySide6.QtGui import QTextDocument, QPageSize
from PySide6.QtPrintSupport import QPrinter, QPrintDialog
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QDialog,
    QDialogButtonBox, QDoubleSpinBox, QTextEdit, QAbstractItemView, QTabWidget,
    QFrame, QGridLayout
)
from app.services.sales_invoice_service import SalesInvoiceService
from app.services.sales_return_service import SalesReturnService
from app.ui.theme import APP_STYLE


def money(value):
    return f"{float(value or 0):,.2f}"


class ReturnDialog(QDialog):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.rows = SalesInvoiceService.returnable_items(data)
        self.setWindowTitle("مرتجع مبيعات — جزئي أو كامل")
        self.resize(980, 560)
        self.setLayoutDirection(Qt.RightToLeft)

        root = QVBoxLayout(self)
        root.addWidget(QLabel("حدد كمية المرتجع لكل صنف. اترك الكمية صفرًا إذا لم ترد الصنف."))

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["الصنف", "الأصلي", "مرتجع سابقًا", "المتاح", "كمية المرتجع", "السعر"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for column in range(1, 6):
            self.table.horizontalHeader().setSectionResizeMode(column, QHeaderView.Fixed)
            self.table.horizontalHeader().resizeSection(column, 125)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.verticalHeader().setDefaultSectionSize(42)

        for item in self.rows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = [
                item["name_ar"],
                item["original_quantity"],
                item["returned_quantity"],
                item["available_quantity"],
                "",
                money(item["unit_price"]),
            ]
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))
            spin = QDoubleSpinBox()
            spin.setRange(0, item["available_quantity"])
            spin.setDecimals(3)
            spin.setAlignment(Qt.AlignCenter)
            self.table.setCellWidget(row, 4, spin)

        root.addWidget(self.table, 1)

        self.reason = QTextEdit()
        self.reason.setPlaceholderText("سبب المرتجع — مطلوب")
        self.reason.setMaximumHeight(90)
        root.addWidget(self.reason)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _accept(self):
        if not self.reason.toPlainText().strip():
            QMessageBox.warning(self, "بيانات ناقصة", "سبب المرتجع مطلوب.")
            return
        if not any(
            self.table.cellWidget(row, 4).value() > 0
            for row in range(self.table.rowCount())
        ):
            QMessageBox.warning(self, "بيانات ناقصة", "حدد كمية مرتجع واحدة على الأقل.")
            return
        self.accept()

    def values(self):
        items = []
        for row, item in enumerate(self.rows):
            quantity = self.table.cellWidget(row, 4).value()
            if quantity > 0:
                items.append({
                    "product_id": item["product_id"],
                    "quantity": quantity,
                })
        return items, self.reason.toPlainText().strip()


class SalesInvoiceWindow(QWidget):
    """ملف فاتورة 360° مرتب: رأس الفاتورة، الأصناف، المدفوعات، المرتجعات والتدقيق."""

    def __init__(self, parent=None, sale_id=None, data=None):
        super().__init__(parent)
        self.setWindowTitle("فاتورة البيع — الملف الكامل")
        self.setMinimumSize(1280, 820)
        self.setLayoutDirection(Qt.RightToLeft)
        self.data = data

        self.setStyleSheet(APP_STYLE)
      root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("ملف فاتورة البيع")
        title.setStyleSheet("font-size:28px;font-weight:700;")
        header.addWidget(title)
        header.addStretch()

        self.search = QLineEdit()
        self.search.setMinimumWidth(280)
        self.search.setPlaceholderText("أدخل رقم الفاتورة ثم Enter")
        self.search.returnPressed.connect(self.load_by_number)
        find = QPushButton("فتح")
        find.clicked.connect(self.load_by_number)
        header.addWidget(self.search)
        header.addWidget(find)
        root.addLayout(header)

        actions = QHBoxLayout()
        return_button = QPushButton("مرتجع جزئي / كامل")
        return_button.clicked.connect(self.create_return)
        print_button = QPushButton("طباعة الفاتورة")
        print_button.clicked.connect(self.print_invoice)
        actions.addWidget(return_button)
        actions.addWidget(print_button)
        actions.addStretch()
        root.addLayout(actions)

        self.identity = QLabel("أدخل رقم الفاتورة لعرض الملف الكامل")
        self.identity.setStyleSheet("font-size:21px;font-weight:700;")
        root.addWidget(self.identity)

        self.meta = QLabel("")
        self.meta.setStyleSheet("color:#9FB2C8;padding-bottom:4px;")
        self.meta.setWordWrap(True)
        root.addWidget(self.meta)

        self.tabs = QTabWidget()
        self.items = self._table(
            ["الكود", "الصنف", "الكمية", "سعر الوحدة", "الخصم", "الضريبة", "الإجمالي"]
        )
        self.payments = self._table(["طريقة الدفع", "المبلغ", "التاريخ"])
        self.returns = self._table(["رقم المرتجع", "المبلغ", "السبب", "الحالة", "التاريخ"])
        self.history = self._table(["التاريخ", "الإجراء"])

        self.tabs.addTab(self.items, "الأصناف")
        self.tabs.addTab(self.payments, "المدفوعات")
        self.tabs.addTab(self.returns, "المرتجعات")
        self.tabs.addTab(self.history, "السجل والتدقيق")
        root.addWidget(self.tabs, 1)

        totals_title = QLabel("ملخص الفاتورة")
        totals_title.setStyleSheet("font-size:17px;font-weight:700;padding-top:4px;")
        root.addWidget(totals_title)

        self.metrics_layout = QGridLayout()
        self.metrics_layout.setHorizontalSpacing(10)
        self.metrics_layout.setVerticalSpacing(10)
        for column in range(4):
            self.metrics_layout.setColumnStretch(column, 1)

        self.metric_labels = {}
        for index, (key, title_text) in enumerate([
            ("subtotal", "قبل الضريبة"),
            ("discount", "الخصم"),
            ("tax", "الضريبة"),
            ("total", "الإجمالي"),
            ("returned", "المرتجع"),
            ("paid", "المدفوع"),
            ("due", "المتبقي"),
        ]):
            card = QFrame()
            card.setObjectName("MetricCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 9, 12, 9)
            label = QLabel(title_text)
            label.setStyleSheet("color:#9FB2C8;font-size:12px;")
            value = QLabel("0.00")
            value.setStyleSheet("font-size:18px;font-weight:700;")
            card_layout.addWidget(label)
            card_layout.addWidget(value)
            row, column = divmod(index, 4)
            self.metrics_layout.addWidget(card, row, column)
            self.metric_labels[key] = value

        root.addLayout(self.metrics_layout)

        if self.data:
            self.search.setText(str(self.data["sale"].get("invoice_number") or ""))
            self.render()
        elif sale_id is not None:
            self.load_sale(sale_id)

    @staticmethod
    def find_data_by_number(number):
        return SalesInvoiceService.find_by_number(str(number or "").strip())

    @staticmethod
    def _table(headers):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setDefaultSectionSize(42)
        table.horizontalHeader().setStretchLastSection(True)

        if len(headers) > 1:
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
            table.horizontalHeader().resizeSection(0, 135)
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

        return table

    @staticmethod
    def _fill(table, rows):
        table.setRowCount(0)
        for values in rows:
            row = table.rowCount()
            table.insertRow(row)
            for column, value in enumerate(values):
                item = QTableWidgetItem("" if value is None else str(value))
                item.setTextAlignment(Qt.AlignCenter if column != 1 else Qt.AlignRight | Qt.AlignVCenter)
                table.setItem(row, column, item)

    def load_by_number(self):
        number = self.search.text().strip()
        if not number:
            return

        data = self.find_data_by_number(number)
        if not data:
            QMessageBox.warning(self, "غير موجود", "لم يتم العثور على فاتورة بهذا الرقم.")
            self.search.selectAll()
            self.search.setFocus()
            return

        self.data = data
        self.render()

    def load_sale(self, sale_id):
        data = SalesInvoiceService.get(sale_id)
        if not data:
            QMessageBox.warning(self, "غير موجود", "الفاتورة غير موجودة.")
            return
        self.data = data
        self.search.setText(str(data["sale"].get("invoice_number") or ""))
        self.render()

    @staticmethod
    def status_ar(value):
        return {
            "POSTED": "مرحّلة",
            "DRAFT": "مسودة",
            "VOID": "ملغاة",
            "CANCELLED": "ملغاة",
        }.get(str(value), str(value or ""))

    @staticmethod
    def payment_ar(value):
        return {
            "CASH": "نقدي",
            "CARD": "بطاقة",
            "TRANSFER": "تحويل",
            "BANK_TRANSFER": "تحويل بنكي",
            "CREDIT": "آجل",
            "credit": "آجل",
        }.get(str(value), str(value or ""))

    def render(self):
        sale = self.data["sale"]
        status = self.status_ar(sale.get("status"))

        self.identity.setText(
            f"فاتورة رقم: {sale.get('invoice_number', '')} — الحالة: {status}"
        )
        self.meta.setText(
            f"التاريخ: {sale.get('created_at', '')}   |   "
            f"العميل: {sale.get('customer_id') or 'عميل نقدي'}   |   "
            f"المعرف الداخلي: {sale.get('id')}"
        )

        self._fill(
            self.items,
            [
                (
                    x.get("sku"),
                    x.get("name_ar"),
                    x.get("quantity"),
                    money(x.get("unit_price")),
                    money(x.get("discount_amount") or x.get("discount")),
                    money(x.get("tax_amount")),
                    money(x.get("line_total")),
                )
                for x in self.data["items"]
            ],
        )

        self._fill(
            self.payments,
            [
                (
                    self.payment_ar(x.get("payment_method")),
                    money(x.get("amount")),
                    x.get("created_at"),
                )
                for x in self.data["payments"]
            ],
        )

        self._fill(
            self.returns,
            [
                (
                    x.get("return_number"),
                    money(x.get("total_amount")),
                    x.get("reason"),
                    self.status_ar(x.get("status")),
                    x.get("created_at"),
                )
                for x in self.data["returns"]
            ],
        )

        self._fill(
            self.history,
            [
                (x.get("event_date"), x.get("action"))
                for x in self.data["audit"]
            ],
        )

        sale_total = float(sale.get("total_amount") or 0)
        returned = sum(float(x.get("total_amount") or 0) for x in self.data["returns"])

        values = {
            "subtotal": sale.get("subtotal"),
            "discount": sale.get("discount_amount"),
            "tax": sale.get("tax_amount"),
            "total": sale_total,
            "returned": returned,
            "paid": sale.get("paid_amount"),
            "due": sale.get("due_amount"),
        }
        for key, value in values.items():
            self.metric_labels[key].setText(money(value))

    def create_return(self):
        if not self.data:
            QMessageBox.information(self, "فاتورة", "افتح فاتورة أولاً.")
            return

        dialog = ReturnDialog(self.data, self)
        if dialog.exec() != QDialog.Accepted:
            return

        items, reason = dialog.values()
        try:
            result = SalesReturnService.create_return(
                int(self.data["sale"]["id"]),
                items,
                reason,
            )
            QMessageBox.information(
                self,
                "تم إنشاء المرتجع",
                f"رقم المرتجع: {result['return_number']}\n"
                f"إجمالي المرتجع: {money(result['total'])}",
            )
            self.load_sale(int(self.data["sale"]["id"]))
        except Exception as exc:
            QMessageBox.critical(self, "فشل إنشاء المرتجع", str(exc))

    def print_invoice(self):
        if not self.data:
            QMessageBox.information(self, "فاتورة", "افتح فاتورة أولاً.")
            return

        sale = self.data["sale"]
        doc = QTextDocument()
        html = [
            "<h1 align='center'>فاتورة بيع</h1>",
            f"<p><b>رقم الفاتورة:</b> {sale.get('invoice_number', '')}<br>"
            f"<b>التاريخ:</b> {sale.get('created_at', '')}</p>",
            "<table width='100%' border='1' cellspacing='0' cellpadding='6'>"
            "<tr><th>الصنف</th><th>الكمية</th><th>السعر</th><th>الإجمالي</th></tr>",
        ]
        for item in self.data["items"]:
            html.append(
                f"<tr><td>{item.get('name_ar', '')}</td>"
                f"<td>{item.get('quantity', 0)}</td>"
                f"<td>{money(item.get('unit_price'))}</td>"
                f"<td>{money(item.get('line_total'))}</td></tr>"
            )
        html.append("</table>")
        html.append(
            f"<p><b>الإجمالي:</b> {money(sale.get('total_amount'))}<br>"
            f"<b>المدفوع:</b> {money(sale.get('paid_amount'))}<br>"
            f"<b>المتبقي:</b> {money(sale.get('due_amount'))}</p>"
        )

        doc.setHtml("".join(html))
        printer = QPrinter(QPrinter.HighResolution)
        printer.setPageSize(QPageSize(QPageSize.A4))
        dialog = QPrintDialog(printer, self)
        if dialog.exec() == QDialog.Accepted:
            doc.print_(printer)
