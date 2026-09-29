
from app.ui.pos_window import POSWindow
from app.ui.sales_window import SalesWindow
from app.ui.purchases_window import PurchasesWindow
from app.ui.parties_window import PartiesWindow
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

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle(f"{APP_NAME} - {APP_VERSION}")
        self.setMinimumSize(1200, 720)

        self.setStyleSheet("""
            QMainWindow {
                background: #07111F;
            }

            QLabel {
                color: white;
            }

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

            QPushButton:hover {
                background: #183452;
            }
        """)

        self.build_ui()

    def build_ui(self):
        root = QWidget()
        main = QHBoxLayout(root)
        main.setContentsMargins(16, 16, 16, 16)
        main.setSpacing(16)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(230)

        side_layout = QVBoxLayout(sidebar)

        logo = QLabel("نظام القرطاسية")
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet(
            "font-size:22px;font-weight:bold;padding:20px;"
        )
        side_layout.addWidget(logo)

        for name in [
            "لوحة التحكم",
            "نقطة البيع",
            "المنتجات والمخزون",
            "المبيعات",
            "المشتريات",
            "العملاء",
            "الموردون",
            "الخزينة والبنوك",
            "المحاسبة",
            "التقارير",
            "الموظفون",
            "الإعدادات",
        ]:
            button = QPushButton(name)
            side_layout.addWidget(button)

        side_layout.addStretch()

        version = QLabel(f"الإصدار {APP_VERSION}")
        version.setAlignment(Qt.AlignCenter)
        side_layout.addWidget(version)

        content = QFrame()
        content_layout = QVBoxLayout(content)

        title = QLabel("لوحة التحكم")
        title.setStyleSheet(
            "font-size:30px;font-weight:bold;padding:10px;"
        )
        content_layout.addWidget(title)

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
        content_layout.addWidget(status)

        cards = QHBoxLayout()

        data = [
            ("المنتجات", summary["products"]),
            ("العملاء", summary["customers"]),
            ("الموردون", summary["suppliers"]),
            ("المبيعات", summary["sales"]),
            ("المشتريات", summary["purchase_invoices"]),
            ("المخزون", financial["inventory"]),
        ]

        for name, value in data:
            card = QFrame()
            card.setObjectName("Card")

            layout = QVBoxLayout(card)

            label = QLabel(name)
            label.setAlignment(Qt.AlignCenter)

            number = QLabel(str(value))
            number.setAlignment(Qt.AlignCenter)
            number.setStyleSheet(
                "font-size:24px;font-weight:bold;"
            )

            layout.addWidget(label)
            layout.addWidget(number)

            cards.addWidget(card)

        content_layout.addLayout(cards)

        info = QLabel(
            "النظام متصل مباشرة بقاعدة البيانات الحالية.\n"
            "هذه الواجهة هي الأساس الذي ستبنى عليه الوحدات التشغيلية."
        )
        info.setStyleSheet(
            "font-size:16px;padding:20px;"
        )
        content_layout.addWidget(info)

        content_layout.addStretch()

        main.addWidget(sidebar)
        main.addWidget(content, 1)

        self.setCentralWidget(root)


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
