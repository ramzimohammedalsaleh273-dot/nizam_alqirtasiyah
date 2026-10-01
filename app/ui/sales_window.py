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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(APP_STYLE)
        self.setWindowTitle("المبيعات والفواتير")
        self.setMinimumSize(1250, 720)
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
            QLineEdit {
                background:#0E1C2D;
                color:#FFFFFF;
                border:1px solid #29445F;
                border-radius:8px;
                padding:10px;
            }
            QPushButton { padding:9px 14px; min-height:36px; }
        """)

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
            "المعرف", "رقم الفاتورة", "قبل الضريبة", "الخصم",
            "الضريبة", "الإجمالي", "المدفوع", "المتبقي"
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

    def load(self):
        try:
            rows = SalesService.list_sales()
            self.table.setRowCount(0)

            for row_data in rows:
                row = self.table.rowCount()
                self.table.insertRow(row)

                values = [
                    row_data["id"],
                    row_data["invoice_number"],
                    f'{float(row_data["subtotal"] or 0):,.2f}',
                    f'{float(row_data["discount_amount"] or 0):,.2f}',
                    f'{float(row_data["tax_amount"] or 0):,.2f}',
                    f'{float(row_data["total_amount"] or 0):,.2f}',
                    f'{float(row_data["paid_amount"] or 0):,.2f}',
                    f'{float(row_data["due_amount"] or 0):,.2f}',
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

        window = SalesInvoiceWindow(self, data=data)
        window.show()
        window.raise_()
        window.activateWindow()
        self._invoice_window = window

    def show_details(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "تنبيه", "اختر فاتورة أولاً.")
            return

        sale_id = int(self.table.item(row, 0).text())
        window = SalesInvoiceWindow(self, sale_id=sale_id)
        window.show()
        window.raise_()
        window.activateWindow()
        self._invoice_window = window

# UI reference theme is applied by the main application shell.
