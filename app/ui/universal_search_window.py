from collections import defaultdict
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QFrame,
    QMessageBox, QTabWidget, QToolButton
)
from app.services.universal_search_service import UniversalSearchService
from app.services.smart_insights_service import SmartInsightsService


class UniversalSearchWindow(QWidget):
    """ملف موحّد 360°؛ البحث والملف والتاريخ والإجراءات في شاشة واحدة."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("مركز الملف 360°")
        self.setMinimumSize(1320, 820)
        self.setLayoutDirection(Qt.RightToLeft)
        self.results = []

        root = QVBoxLayout(self)

        header = QHBoxLayout()
        title = QLabel("مركز الملف 360°")
        title.setStyleSheet("font-size:28px;font-weight:bold;")
        header.addWidget(title)
        header.addStretch()
        self.entity_selector = QComboBox()
        self.entity_selector.setMinimumWidth(420)
        self.entity_selector.currentIndexChanged.connect(self.select_result)
        header.addWidget(self.entity_selector)
        root.addLayout(header)

        search_bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("ابحث عن منتج أو عميل أو مورد أو فاتورة أو حساب أو موظف أو مستودع...")
        self.search.returnPressed.connect(self.load_results)
        button = QPushButton("بحث")
        button.clicked.connect(self.load_results)
        clear = QPushButton("مسح")
        clear.clicked.connect(self.clear_all)
        search_bar.addWidget(self.search, 1)
        search_bar.addWidget(button)
        search_bar.addWidget(clear)
        root.addLayout(search_bar)

        self.identity = QFrame()
        self.identity.setStyleSheet("QFrame{background:#101F33;border:1px solid #1E3856;border-radius:14px;}")
        identity_layout = QVBoxLayout(self.identity)
        self.title_label = QLabel("اكتب ما تبحث عنه")
        self.title_label.setStyleSheet("font-size:24px;font-weight:bold;")
        self.meta_label = QLabel("سيظهر هنا ملخص الحالة والهوية والرصيد والمخزون.")
        self.meta_label.setWordWrap(True)
        identity_layout.addWidget(self.title_label)
        identity_layout.addWidget(self.meta_label)
        root.addWidget(self.identity)

        actions = QHBoxLayout()
        for text, slot in [
            ("تعديل", self.open_admin),
            ("فتح شاشة الإدارة", self.open_admin),
            ("نسخ رقم/كود", self.copy_code),
        ]:
            b = QPushButton(text)
            b.clicked.connect(slot)
            actions.addWidget(b)
        actions.addStretch()
        root.addLayout(actions)

        self.tabs = QTabWidget()
        self.summary = self._table(["المؤشر", "القيمة"])
        self.data = self._table(["البيان", "القيمة"])
        self.timeline = self._table(["التاريخ", "النوع", "المستند", "الطرف", "الكمية", "القيمة"])
        self.alerts = self._table(["النوع", "التنبيه"])
        self.stock = self._table(["المستودع", "المخزون", "المتاح", "متوسط التكلفة"])
        self.tabs.addTab(self.summary, "نظرة عامة")
        self.tabs.addTab(self.timeline, "التاريخ اليومي")
        self.tabs.addTab(self.stock, "المخزون")
        self.tabs.addTab(self.alerts, "التنبيهات")
        self.tabs.addTab(self.data, "كل البيانات")
        root.addWidget(self.tabs, 1)

        self.status = QLabel("جاهز.")
        root.addWidget(self.status)

    @staticmethod
    def _table(headers):
        t = QTableWidget(0, len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        t.horizontalHeader().setStretchLastSection(True)
        t.setEditTriggers(QTableWidget.NoEditTriggers)
        t.setSelectionBehavior(QTableWidget.SelectRows)
        return t

    @staticmethod
    def _fill(table, rows):
        table.setRowCount(0)
        for values in rows:
            r = table.rowCount()
            table.insertRow(r)
            for c, value in enumerate(values):
                table.setItem(r, c, QTableWidgetItem("" if value is None else str(value)))

    def clear_all(self):
        self.search.clear()
        self.entity_selector.clear()
        self.results = []
        self.title_label.setText("اكتب ما تبحث عنه")
        self.meta_label.setText("سيظهر هنا الملف الكامل.")
        for t in (self.summary, self.data, self.timeline, self.alerts, self.stock):
            t.setRowCount(0)

    def load_results(self):
        try:
            self.results = UniversalSearchService.search(self.search.text().strip(), limit=80)
            self.entity_selector.blockSignals(True)
            self.entity_selector.clear()
            for r in self.results:
                self.entity_selector.addItem(
                    f"{r['kind_name']} — {r['name']} — {r.get('subtitle','')}", r
                )
            self.entity_selector.blockSignals(False)
            self.status.setText(f"تم العثور على {len(self.results)} نتيجة. اختر من نفس الشاشة لفتح الملف الكامل.")
            if self.results:
                self.entity_selector.setCurrentIndex(0)
                self.show_profile(self.results[0])
            else:
                self.clear_all()
                self.status.setText("لا توجد نتائج.")
        except Exception as exc:
            QMessageBox.critical(self, "فشل البحث", str(exc))

    def select_result(self, index):
        if 0 <= index < len(self.results):
            self.show_profile(self.results[index])

    def show_profile(self, item):
        try:
            profile = SmartInsightsService.profile(item["kind"], int(item["id"]))
            if not profile:
                QMessageBox.warning(self, "لا توجد بيانات", "تعذر بناء ملف هذا الكيان.")
                return
            self.current_profile = profile
            self.current_item = item
            self.title_label.setText(profile.get("title", item["name"]))
            metrics = profile.get("metrics") or profile.get("summary") or []
            self._fill(self.summary, metrics)
            self._fill(self.alerts, profile.get("alerts", []))
            self._fill(self.data, [
                (k, v) for k, v in profile.get("data", {}).items()
                if not str(k).startswith("_")
            ])
            self._fill(self.stock, [
                (x.get("warehouse_name"), x.get("quantity"), x.get("available_quantity"), x.get("average_cost"))
                for x in profile.get("warehouses", [])
            ])

            events = []
            for x in profile.get("sales", []):
                events.append((x.get("event_date"), "بيع", x.get("invoice_number"),
                               x.get("customer_name") or "نقدي/غير محدد", x.get("quantity"), x.get("amount")))
            for x in profile.get("purchases", []):
                events.append((x.get("event_date"), "شراء", x.get("invoice_number"),
                               x.get("supplier_name") or "غير محدد", x.get("quantity"), x.get("amount")))
            for x in profile.get("documents", []):
                events.append((x.get("event_date"), "مستند", x.get("invoice_number"),
                               "", "", x.get("total_amount")))

            events.sort(key=lambda x: str(x[0] or ""), reverse=True)
            grouped = defaultdict(list)
            for e in events:
                date = str(e[0] or "بدون تاريخ")[:10]
                grouped[date].append(e)

            timeline_rows = []
            for day, day_events in grouped.items():
                timeline_rows.append((f"━━ {day} ━━", "", "", "", "", ""))
                timeline_rows.extend(day_events)
            self._fill(self.timeline, timeline_rows)

            self.meta_label.setText(
                f"النوع: {item['kind_name']}    |    الكود: {profile.get('code','')}    |    "
                f"النتائج مرتبطة بملف واحد وتاريخ زمني مجمّع حسب اليوم."
            )
            self.status.setText(f"ملف كامل جاهز — {len(events)} حركة/مستند.")
        except Exception as exc:
            QMessageBox.critical(self, "فشل الملف 360°", str(exc))

    def open_admin(self):
        if not getattr(self, "current_item", None):
            return
        kind = self.current_item["kind"]
        if kind == "product":
            from app.ui.inventory_window import InventoryWindow
            self.admin_window = InventoryWindow()
        elif kind in {"customer", "supplier"}:
            from app.ui.parties_window import PartiesWindow
            self.admin_window = PartiesWindow()
        else:
            QMessageBox.information(self, "الإجراء", "هذا النوع يُدار من شاشته المتخصصة.")
            return
        self.admin_window.show()
        self.admin_window.raise_()
        self.admin_window.activateWindow()

    def copy_code(self):
        profile = getattr(self, "current_profile", None)
        if profile:
            QApplication.clipboard().setText(str(profile.get("code") or ""))
            self.status.setText("تم نسخ الكود إلى الحافظة.")

