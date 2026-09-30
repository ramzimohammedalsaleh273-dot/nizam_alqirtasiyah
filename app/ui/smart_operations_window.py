from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QMessageBox
from app.services.smart_operations_service import SmartOperationsService


class SmartOperationsWindow(QWidget):
    """مركز التشغيل الذكي: لقطة فورية لما يحتاج المتابعة."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("مركز التشغيل الذكي")
        self.setMinimumSize(1000, 650)
        self.setLayoutDirection(Qt.RightToLeft)

        root = QVBoxLayout(self)
        title = QLabel("مركز التشغيل الذكي")
        title.setStyleSheet("font-size:28px;font-weight:bold;padding:10px;")
        root.addWidget(title)

        subtitle = QLabel("بدل البحث في عشرات الشاشات: هنا ترى أهم الأشياء التي تستحق الانتباه الآن.")
        subtitle.setStyleSheet("color:#8ea6c2;padding:0 10px 10px;")
        root.addWidget(subtitle)

        self.cards = QHBoxLayout()
        root.addLayout(self.cards)

        actions = QHBoxLayout()
        refresh = QPushButton("تحديث المؤشرات")
        refresh.clicked.connect(self.load)
        search = QPushButton("فتح البحث 360°")
        search.clicked.connect(self.open_search)
        actions.addWidget(refresh)
        actions.addWidget(search)
        actions.addStretch()
        root.addLayout(actions)

        self.message = QLabel("")
        self.message.setWordWrap(True)
        self.message.setStyleSheet("font-size:16px;padding:16px;")
        root.addWidget(self.message)
        root.addStretch()
        self.load()

    def load(self):
        try:
            data = SmartOperationsService.snapshot()
            while self.cards.count():
                item = self.cards.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            values = [
                ("أصناف تحتاج متابعة", data["low_stock"]),
                ("ذمم العملاء", f"{data['customer_due']:.2f}"),
                ("ذمم الموردين", f"{data['supplier_due']:.2f}"),
                ("قيود غير متوازنة", data["unbalanced"]),
            ]
            for label, value in values:
                card = QFrame()
                card.setStyleSheet("QFrame{background:#101F33;border:1px solid #1E3856;border-radius:14px;}")
                layout = QVBoxLayout(card)
                l = QLabel(label)
                l.setAlignment(Qt.AlignCenter)
                n = QLabel(str(value))
                n.setAlignment(Qt.AlignCenter)
                n.setStyleSheet("font-size:25px;font-weight:bold;")
                layout.addWidget(l)
                layout.addWidget(n)
                self.cards.addWidget(card)

            warnings = []
            if data["low_stock"]:
                warnings.append(f"يوجد {data['low_stock']} صنفًا عند/دون نقطة إعادة الطلب.")
            if data["customer_due"] > 0:
                warnings.append(f"إجمالي الذمم المدينة الحالية: {data['customer_due']:.2f}.")
            if data["supplier_due"] > 0:
                warnings.append(f"إجمالي الذمم الدائنة الحالية: {data['supplier_due']:.2f}.")
            if data["unbalanced"]:
                warnings.append("يوجد قيد محاسبي غير متوازن ويجب عدم تجاهله.")
            if not warnings:
                warnings.append("لا توجد مؤشرات حرجة في اللقطة الحالية.")
            self.message.setText("\n".join("• " + x for x in warnings))
        except Exception as exc:
            QMessageBox.critical(self, "فشل مركز التشغيل", str(exc))

    def open_search(self):
        from app.ui.universal_search_window import UniversalSearchWindow
        self.search_window = UniversalSearchWindow()
        self.search_window.show()
        self.search_window.raise_()
        self.search_window.activateWindow()
