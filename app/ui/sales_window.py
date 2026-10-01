from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QLabel, QMessageBox, QLineEdit,
    QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt
from app.services.sales_service import SalesService
from app.ui.sales_invoice_window import SalesInvoiceWindow
from app.ui.theme import APP_STYLE


class SalesWindow(QWidget):
    """سجل المبيعات بجدول واضح وبحث مباشر برقم الفاتورة."""

    def __init__(self, user=None, parent=None):
        super().__init__(parent)
        self.user = dict(user or {})
        self.setStyleSheet(APP_STYLE)
        self.setWindowTitle("المبيعات والفواتير")
        self.setMinimumSize(1250, 720)
        self.setLayoutDirection(Qt.RightToLeft)

        self.setStyleSheet(APP_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel("المبيعات والفواتير")
        title.setStyleSheet("font-size:28px;font-weight:700;")
        layout.addWidget(title)

        subtitle = QLabel("ابحث برقم الفاتورة ثم افتح ملفها الكامل. يمكنك أيضًا فتح أي صف بالنقر المزدوج.")
        subtitle.setStyleSheet("color:#9FB2C8;")
        layout.addWidget(subtitle)

        bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("رقم الفاتورة...")
        self.search.returnPressed.connect(self.open_by_number)
        self.search.textChanged.connect(lambda _: self._live_filter())

        search_button = QPushButton("فتح الفاتورة")
        search_button.clicked.connect(self.open_by_number)

        refresh = QPushButton("تحديث")
        refresh.clicked.connect(self.load)

        bar.addWidget(self.search, 1)
        bar.addWidget(search_button)
        bar.addWidget(refresh)
        layout.addLayout(bar)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([
            "رقم", "التاريخ", "العميل", "المستخدم",
            "الإجمالي", "المدفوع", "المتبقي", "الحالة"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.resizeSection(0, 80)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.resizeSection(1, 190)
        for column in range(2, 8):
            header.setSectionResizeMode(column, QHeaderView.Fixed)
            header.resizeSection(column, 125)

        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setDefaultSectionSize(42)
        self.table.doubleClicked.connect(lambda *_: self.show_details())

        layout.addWidget(self.table, 1)

        self.status = QLabel("جاهز")
        self.status.setStyleSheet("color:#9FB2C8;padding:4px;")
        layout.addWidget(self.status)

        self.load()

    def _live_filter(self):
        term = self.search.text().strip()
        if term:
            rows = [r for r in SalesService.list_sales() if any(term.lower() in str(r.get(k) or "").lower() for k in ("invoice_number","customer_name","cashier_name","status"))]
            self._render_rows(rows)
        else:
            self.load()

    def _render_rows(self, rows):
        self.table.setRowCount(0)
        for row_data in rows:
            row = self.table.rowCount(); self.table.insertRow(row)
            values=[row_data["invoice_number"],row_data["created_at"],row_data.get("customer_name") or "نقدي",row_data.get("cashier_name") or "—",f'{float(row_data["total_amount"] or 0):,.2f}',f'{float(row_data["paid_amount"] or 0):,.2f}',f'{float(row_data["due_amount"] or 0):,.2f}',row_data.get("status") or ""]
            for column,value in enumerate(values):
                item=QTableWidgetItem(str(value)); item.setTextAlignment(Qt.AlignCenter); self.table.setItem(row,column,item)
        self.status.setText(f"تم تحميل {len(rows)} فاتورة.")

    def load(self):
        try:
            rows = SalesService.list_sales()
            self.table.setRowCount(0)

            for row_data in rows:
                row = self.table.rowCount()
                self.table.insertRow(row)

                values = [
                    row_data["invoice_number"],
                    row_data["created_at"],
                    row_data.get("customer_name") or "نقدي",
                    row_data.get("cashier_name") or "—",
                    f'{float(row_data["total_amount"] or 0):,.2f}',
                    f'{float(row_data["paid_amount"] or 0):,.2f}',
                    f'{float(row_data["due_amount"] or 0):,.2f}',
                    row_data.get("status") or "",
                ]

                for column, value in enumerate(values):
                    item = QTableWidgetItem(str(value))
                    item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row, column, item)

            self.status.setText(f"تم تحميل {len(rows)} فاتورة.")
        except Exception as exc:
            self.status.setText("تعذر تحميل سجل المبيعات.")
            QMessageBox.critical(self, "خطأ في المبيعات", str(exc))

    def open_by_number(self):
        number = self.search.text().strip()
        if not number:
            self.search.setFocus()
            return

        data = SalesInvoiceWindow.find_data_by_number(number)
        if not data:
            QMessageBox.warning(self, "غير موجود", "لم يتم العثور على فاتورة بهذا الرقم.")
            self.search.selectAll()
            self.search.setFocus()
            return

        window = SalesInvoiceWindow(self.user, self, data=data)
        window.show()
        window.raise_()
        window.activateWindow()
        self._invoice_window = window

    def show_details(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "تنبيه", "اختر فاتورة أولاً.")
            return

        invoice_number = self.table.item(row, 0).text()
        data = SalesInvoiceWindow.find_data_by_number(invoice_number)
        if not data:
            QMessageBox.warning(self, "غير موجود", "تعذر فتح الفاتورة المحددة.")
            return
        sale_id = int(data["sale"]["id"])
        window = SalesInvoiceWindow(self.user, self, sale_id=sale_id)
        window.show()
        window.raise_()
        window.activateWindow()
        self._invoice_window = window

# UI reference theme is applied by the main application shell.
