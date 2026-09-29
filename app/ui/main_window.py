from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QMessageBox
)
from PySide6.QtCore import Qt
from app.core.config import APP_NAME, APP_VERSION
from app.services.system_service import (
    get_system_summary,
    get_financial_summary,
    get_health,
)
from app.ui.pos_window import POSWindow
from app.ui.sales_window import SalesWindow
from app.ui.purchases_window import PurchasesWindow
from app.ui.parties_window import PartiesWindow
from app.ui.inventory_window import InventoryWindow
from app.ui.reports_window import ReportsWindow


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle(f"{APP_NAME} - {APP_VERSION}")
        self.setMinimumSize(1200, 720)
        self._child_windows = {}
        self.build_ui()

    def build_ui(self):
        self.setStyleSheet("""
            QMainWindow { background: #07111F; }
            QLabel { color: white; }
            QFrame#Sidebar {
                background: #0B1728;
                border-radius: 12px;
            }
            QFrame#Card {
                background: #101F33;
                border: 1px solid #1E3856;
                border-radius: 14px;
            }
            QPushButton {
                background: #13263D;
                color: white;
                border: 1px solid #244566;
                border-radius: 8px;
                padding: 10px;
                text-align: right;
            }
            QPushButton:hover { background: #183452; }
        """)

        root = QWidget()
        main = QHBoxLayout(root)
        main.setContentsMargins(16, 16, 16, 16)
        main.setSpacing(16)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(250)
        side_layout = QVBoxLayout(sidebar)

        logo = QLabel("نظام القرطاسية")
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet(
            "font-size:22px;font-weight:bold;padding:20px;"
        )
        side_layout.addWidget(logo)

        navigation = [
            ("لوحة التحكم", self.show_dashboard),
            ("نقطة البيع", self.open_pos),
            ("المنتجات والمخزون", self.open_inventory),
            ("المبيعات", self.open_sales),
            ("المشتريات", self.open_purchases),
            ("العملاء والموردون", self.open_parties),
            ("الخزينة والبنوك", self.not_ready),
            ("المحاسبة", self.not_ready),
            ("التقارير", self.open_reports),
            ("الموظفون", self.not_ready),
            ("الإعدادات", self.not_ready),
        ]

        for name, handler in navigation:
            button = QPushButton(name)
            button.clicked.connect(handler)
            side_layout.addWidget(button)

        side_layout.addStretch()

        version = QLabel(f"الإصدار {APP_VERSION}")
        version.setAlignment(Qt.AlignCenter)
        side_layout.addWidget(version)

        self.content = QFrame()
        self.content_layout = QVBoxLayout(self.content)

        main.addWidget(sidebar)
        main.addWidget(self.content, 1)

        self.setCentralWidget(root)
        self.show_dashboard()

    def clear_content(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def show_dashboard(self):
        self.clear_content()

        title = QLabel("لوحة التحكم")
        title.setStyleSheet(
            "font-size:30px;font-weight:bold;padding:10px;"
        )
        self.content_layout.addWidget(title)

        try:
            health = get_health()
            summary = get_system_summary()
            financial = get_financial_summary()

            status = QLabel(
                "● قاعدة البيانات سليمة"
                if health["healthy"]
                else "● توجد مشكلة في قاعدة البيانات"
            )
            status.setStyleSheet(
                "font-size:16px;font-weight:bold;padding:8px;"
            )
            self.content_layout.addWidget(status)

            cards = QHBoxLayout()
            data = [
                ("المنتجات", summary["products"]),
                ("العملاء", summary["customers"]),
                ("الموردون", summary["suppliers"]),
                ("المبيعات", summary["sales"]),
                ("المشتريات", summary["purchase_invoices"]),
                ("المخزون", summary["stock"]),
            ]

            for name, value in data:
                card = QFrame()
                card.setObjectName("Card")
                card_layout = QVBoxLayout(card)

                label = QLabel(name)
                label.setAlignment(Qt.AlignCenter)

                number = QLabel(str(value))
                number.setAlignment(Qt.AlignCenter)
                number.setStyleSheet(
                    "font-size:24px;font-weight:bold;"
                )

                card_layout.addWidget(label)
                card_layout.addWidget(number)
                cards.addWidget(card)

            self.content_layout.addLayout(cards)

            financial_text = (
                f"النقدية: {financial['cash']:.2f}    "
                f"البنوك: {financial['banks']:.2f}    "
                f"العملاء: {financial['customers']:.2f}    "
                f"المخزون: {financial['inventory']:.2f}"
            )
            financial_label = QLabel(financial_text)
            financial_label.setStyleSheet("font-size:16px;padding:20px;")
            self.content_layout.addWidget(financial_label)

        except Exception as exc:
            QMessageBox.critical(
                self, "خطأ في لوحة التحكم", str(exc)
            )

        self.content_layout.addStretch()

    def open_window(self, key, window_class):
        window = self._child_windows.get(key)
        if window is None:
            window = window_class()
            self._child_windows[key] = window

        window.show()
        window.raise_()
        window.activateWindow()

    def open_pos(self):
        self.open_window("pos", POSWindow)

    def open_inventory(self):
        self.open_window("inventory", InventoryWindow)

    def open_sales(self):
        self.open_window("sales", SalesWindow)

    def open_purchases(self):
        self.open_window("purchases", PurchasesWindow)

    def open_parties(self):
        self.open_window("parties", PartiesWindow)

    def open_reports(self):
        self.open_window("reports", ReportsWindow)

    def not_ready(self):
        button = self.sender()
        name = button.text() if button else "هذه الوحدة"
        QMessageBox.information(
            self,
            name,
            "هذه الوحدة موجودة ضمن خارطة النظام، "
            "لكن واجهتها التشغيلية لم تُربط بعد. "
            "لن نعتبرها مكتملة حتى تُنفذ خدماتها واختباراتها وربطها بقاعدة البيانات."
        )


def run():
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.RightToLeft)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    run()
