from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QListWidget,
    QListWidgetItem, QLabel, QTableWidget, QTableWidgetItem, QSplitter,
    QTabWidget, QFrame, QMessageBox, QHeaderView
)
from app.services.universal_search_service import UniversalSearchService
from app.services.smart_insights_service import SmartInsightsService


class UniversalSearchWindow(QWidget):
    """مركز معلومات 360°: البحث ثم كشف الصورة التشغيلية الكاملة للكيان."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("البحث الذكي ومركز المعلومات 360°")
        self.setMinimumSize(1250, 760)
        self.setLayoutDirection(Qt.RightToLeft)

        root = QVBoxLayout(self)
        title = QLabel("مركز المعلومات 360°")
        title.setStyleSheet("font-size:26px;font-weight:bold;padding:8px;")
        root.addWidget(title)

        hint = QLabel("اكتب أي اسم أو كود أو باركود أو هاتف أو رقم فاتورة — ثم افتح ملفه الكامل.")
        hint.setStyleSheet("color:#8ea6c2;padding:2px 8px 8px;")
        root.addWidget(hint)

        bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("مثال: دفتر، SKU، باركود، اسم عميل، اسم مورد، رقم فاتورة...")
        self.search.returnPressed.connect(self.load_results)
        search_button = QPushButton("بحث")
        search_button.clicked.connect(self.load_results)
        bar.addWidget(self.search, 1)
        bar.addWidget(search_button)
        root.addLayout(bar)

        splitter = QSplitter(Qt.Horizontal)
        self.results = QListWidget()
        self.results.currentItemChanged.connect(self.show_selected)
        splitter.addWidget(self.results)

        self.tabs = QTabWidget()
        self.overview = self._table(["المؤشر", "القيمة"])
        self.alerts = self._table(["النوع", "التنبيه"])
        self.data = self._table(["الحقل", "القيمة"])
        self.warehouses = self._table(["المستودع", "المخزون", "المتاح", "متوسط التكلفة"])
        self.history = self._table(["النوع", "رقم المستند", "التاريخ", "الطرف", "الكمية/الإجمالي", "القيمة"])
        self.tabs.addTab(self.overview, "الملخص")
        self.tabs.addTab(self.alerts, "التنبيهات الذكية")
        self.tabs.addTab(self.data, "بيانات الكيان")
        self.tabs.addTab(self.warehouses, "المخزون حسب المستودع")
        self.tabs.addTab(self.history, "الحركة والتاريخ")
        splitter.addWidget(self.tabs)
        splitter.setSizes([380, 900])
        root.addWidget(splitter)

        self.status = QLabel("جاهز.")
        root.addWidget(self.status)

    @staticmethod
    def _table(headers):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        return table

    def load_results(self):
        try:
            rows = UniversalSearchService.search(self.search.text().strip())
            self.results.clear()
            for row in rows:
                item = QListWidgetItem(
                    f"[{row['kind_name']}] {row['name']} — {row.get('subtitle','')}"
                )
                item.setData(Qt.UserRole, row)
                self.results.addItem(item)
            self.status.setText(f"تم العثور على {len(rows)} نتيجة.")
            if rows:
                self.results.setCurrentRow(0)
            else:
                self.clear_profile()
        except Exception as exc:
            QMessageBox.critical(self, "فشل البحث", str(exc))

    def clear_profile(self):
        for table in (self.overview, self.alerts, self.data, self.warehouses, self.history):
            table.setRowCount(0)

    @staticmethod
    def _fill(table, rows):
        table.setRowCount(0)
        for row in rows:
            r = table.rowCount()
            table.insertRow(r)
            for c, value in enumerate(row):
                table.setItem(r, c, QTableWidgetItem("" if value is None else str(value)))

    def show_selected(self, current, previous=None):
        if current is None:
            self.clear_profile()
            return
        item = current.data(Qt.UserRole)
        kind = item["kind"]
        entity_id = int(item["id"])
        try:
            profile = SmartInsightsService.profile(kind, entity_id)
            if not profile:
                QMessageBox.warning(self, "لا توجد بيانات", "تعذر تكوين ملف 360° لهذا العنصر.")
                return

            self.setWindowTitle(f"360° — {profile['title']}")
            self._fill(self.overview, [(label, value) for label, value in profile.get("metrics", [])])
            self._fill(self.alerts, profile.get("alerts", []))
            self._fill(self.data, [(k, v) for k, v in profile.get("data", {}).items()])

            warehouses = profile.get("warehouses", [])
            self._fill(self.warehouses, [
                (x.get("warehouse_name"), x.get("quantity"), x.get("available_quantity"), x.get("average_cost"))
                for x in warehouses
            ])

            history = []
            for x in profile.get("sales", []):
                history.append(("بيع", x.get("invoice_number"), x.get("event_date"), x.get("customer_name") or "نقدي/غير محدد", x.get("quantity"), x.get("amount")))
            for x in profile.get("purchases", []):
                history.append(("شراء", x.get("invoice_number"), x.get("event_date"), x.get("supplier_name") or "غير محدد", x.get("quantity"), x.get("amount")))
            for x in profile.get("documents", []):
                history.append(("مستند", x.get("invoice_number"), x.get("event_date"), "", "", x.get("total_amount")))
            self._fill(self.history, history)
            self.status.setText(
                f"ملف 360° جاهز: {profile['title']} — "
                f"{len(history)} حركة/مستند معروضة."
            )
        except Exception as exc:
            QMessageBox.critical(self, "فشل ملف 360°", str(exc))
