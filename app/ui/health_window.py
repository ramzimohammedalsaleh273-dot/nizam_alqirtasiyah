from app.ui.theme import APP_STYLE
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QTableWidget, QTableWidgetItem, QHeaderView
from app.services.system_health_service import SystemHealthService


class HealthWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(APP_STYLE)
        self.setWindowTitle("فحص صحة النظام")
        self.setMinimumSize(900, 600)
        layout = QVBoxLayout(self)
        title = QLabel("فحص صحة النظام والبيانات")
        title.setStyleSheet("font-size:28px;font-weight:bold")
        layout.addWidget(title)
        self.status = QLabel()
        self.status.setStyleSheet("font-size:18px;font-weight:bold;padding:8px")
        layout.addWidget(self.status)
        refresh = QPushButton("إعادة الفحص")
        refresh.clicked.connect(self.load)
        layout.addWidget(refresh)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["الفحص", "الحالة", "التفاصيل"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)
        self.load()

    def load(self):
        try:
            result = SystemHealthService.summary()
            self.status.setText("النظام سليم حسب الفحوص الحالية" if result["healthy"] else "توجد نقاط تحتاج إلى معالجة")
            self.table.setRowCount(0)
            for name, ok, details in result["checks"]:
                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(name))
                self.table.setItem(row, 1, QTableWidgetItem("سليم" if ok else "مشكلة"))
                self.table.setItem(row, 2, QTableWidgetItem(details))
        except Exception as exc:
            self.status.setText(f"تعذر إكمال الفحص: {exc}")
