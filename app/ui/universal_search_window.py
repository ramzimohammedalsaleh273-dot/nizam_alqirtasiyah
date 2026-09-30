from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QLabel, QTableWidget, QTableWidgetItem,
    QSplitter, QMessageBox
)
from app.services.universal_search_service import UniversalSearchService


class UniversalSearchWindow(QWidget):
    """بحث شامل مع ملف تشغيلي للمنتج والعميل والمورد."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("البحث الذكي وملفات الكيانات")
        self.setMinimumSize(1150, 700)
        self.setLayoutDirection(Qt.RightToLeft)

        root = QVBoxLayout(self)
        title = QLabel("البحث الذكي — كل ما تحتاجه عن المنتج أو العميل أو المورد")
        title.setStyleSheet("font-size:24px;font-weight:bold;padding:8px;")
        root.addWidget(title)

        bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("ابحث بالاسم، الكود، SKU، الباركود، الهاتف أو رقم الفاتورة...")
        self.search.returnPressed.connect(self.load_results)
        button = QPushButton("بحث")
        button.clicked.connect(self.load_results)
        bar.addWidget(self.search)
        bar.addWidget(button)
        root.addLayout(bar)

        splitter = QSplitter(Qt.Horizontal)
        self.results = QListWidget()
        self.results.currentItemChanged.connect(self.show_selected)
        splitter.addWidget(self.results)

        self.detail = QWidget()
        detail_layout = QVBoxLayout(self.detail)
        self.detail_title = QLabel("اختر نتيجة لعرض الملف الكامل")
        self.detail_title.setStyleSheet("font-size:22px;font-weight:bold;padding:8px;")
        detail_layout.addWidget(self.detail_title)
        self.summary = QTableWidget(0, 2)
        self.summary.setHorizontalHeaderLabels(["المعلومة", "القيمة"])
        self.summary.horizontalHeader().setStretchLastSection(True)
        detail_layout.addWidget(self.summary)
        self.data = QTableWidget(0, 2)
        self.data.setHorizontalHeaderLabels(["الحقل", "القيمة"])
        self.data.horizontalHeader().setStretchLastSection(True)
        detail_layout.addWidget(self.data)
        splitter.addWidget(self.detail)
        splitter.setSizes([420, 700])
        root.addWidget(splitter)

        self.status = QLabel("اكتب كلمة البحث ثم اضغط بحث.")
        root.addWidget(self.status)

    def load_results(self):
        try:
            rows = UniversalSearchService.search(self.search.text().strip())
            self.results.clear()
            for row in rows:
                item = QListWidgetItem(
                    f"[{row['kind_name']}] {row['name']}  —  {row.get('subtitle','')}"
                )
                item.setData(Qt.UserRole, row)
                self.results.addItem(item)
            self.status.setText(f"تم العثور على {len(rows)} نتيجة.")
            if rows:
                self.results.setCurrentRow(0)
            else:
                self.clear_detail()
        except Exception as exc:
            QMessageBox.critical(self, "فشل البحث", str(exc))

    def clear_detail(self):
        self.detail_title.setText("لا توجد نتيجة")
        self.summary.setRowCount(0)
        self.data.setRowCount(0)

    def show_selected(self, current, previous=None):
        if current is None:
            self.clear_detail()
            return
        row = current.data(Qt.UserRole)
        profile = UniversalSearchService.profile(row["kind"], int(row["id"]))
        if not profile:
            self.clear_detail()
            return

        self.detail_title.setText(
            f"{profile['title']}  |  {profile.get('code','')}"
        )

        self.summary.setRowCount(0)
        for label, value in profile["summary"]:
            r = self.summary.rowCount()
            self.summary.insertRow(r)
            self.summary.setItem(r, 0, QTableWidgetItem(str(label)))
            self.summary.setItem(r, 1, QTableWidgetItem(str(value)))

        self.data.setRowCount(0)
        for key, value in profile["data"].items():
            r = self.data.rowCount()
            self.data.insertRow(r)
            self.data.setItem(r, 0, QTableWidgetItem(str(key)))
            self.data.setItem(r, 1, QTableWidgetItem("" if value is None else str(value)))
