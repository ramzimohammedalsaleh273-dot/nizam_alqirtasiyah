from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QMessageBox, QDialog,
    QLineEdit, QDialogButtonBox
)
from PySide6.QtCore import Qt
from app.core.config import APP_NAME, APP_VERSION
from app.services.security_service import SecurityService
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
from app.services.backup_service import BackupService
from app.ui.administration_windows import accounting_window, treasury_window, employees_window, settings_window
from app.ui.health_window import HealthWindow
from app.ui.backup_window import BackupWindow
from app.ui.enterprise_tools_window import EnterpriseToolsWindow
from app.ui.purchase_workflow_window import PurchaseWorkflowWindow
from app.ui.purchase_returns_window import PurchaseReturnsWindow
from app.ui.sales_returns_window import SalesReturnsWindow
from app.ui.treasury_accounts_window import TreasuryAccountsWindow
from app.database.connection import get_session
from app.services.treasury_schema_service import TreasurySchemaService


class LoginDialog(QDialog):
    """بوابة دخول حقيقية قبل فتح واجهة النظام."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.user = None
        self.security = SecurityService()
        self.setWindowTitle("تسجيل الدخول — نظام القرطاسية")
        self.setFixedSize(430, 300)
        self.setLayoutDirection(Qt.RightToLeft)

        layout = QVBoxLayout(self)
        title = QLabel("نظام القرطاسية")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:26px;font-weight:bold;padding:15px;")
        layout.addWidget(title)

        self.username = QLineEdit()
        self.username.setPlaceholderText("اسم المستخدم")
        layout.addWidget(self.username)

        self.password = QLineEdit()
        self.password.setPlaceholderText("كلمة المرور")
        self.password.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password)

        self.message = QLabel("")
        self.message.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.message)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.login)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.password.returnPressed.connect(self.login)
        self.username.setFocus()

    def login(self):
        try:
            user = self.security.authenticate(
                self.username.text().strip(),
                self.password.text(),
            )
        except Exception as exc:
            self.message.setText(f"تعذر تسجيل الدخول: {exc}")
            return
        if not user:
            self.message.setText("اسم المستخدم أو كلمة المرور غير صحيحة.")
            return
        self.user = user
        self.accept()


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle(f"{APP_NAME} - {APP_VERSION}")
        self.setMinimumSize(1200, 720)
        self._child_windows = {}
        self._bootstrap_operational_schema()
        self.build_ui()

    def _bootstrap_operational_schema(self):
        with get_session() as s:
            TreasurySchemaService.ensure(s)
            s.commit()

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
            ("مرتجعات المبيعات", self.open_sales_returns),
            ("المشتريات", self.open_purchases),
            ("دورة المشتريات", self.open_purchase_workflow),
            ("مرتجعات المشتريات", self.open_purchase_returns),
            ("العملاء والموردون", self.open_parties),
            ("الخزينة والبنوك", self.open_treasury),
            ("حسابات الخزينة والتحويلات", self.open_treasury_accounts),
            ("المحاسبة", self.open_accounting),
            ("التقارير", self.open_reports),
            ("الموظفون", self.open_employees),
            ("الإعدادات", self.open_settings),
            ("مركز التشغيل والفحص", self.open_enterprise_tools),
        ]

        for name, handler in navigation:
            button = QPushButton(name)
            button.clicked.connect(handler)
            side_layout.addWidget(button)

        health_button = QPushButton("فحص صحة النظام")
        health_button.clicked.connect(self.open_health)
        side_layout.addWidget(health_button)

        backup = QPushButton("إنشاء نسخة احتياطية")
        backup.clicked.connect(self.open_backup)
        side_layout.addWidget(backup)

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
                ("أصناف منخفضة", summary["low_stock"]),
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

    def open_sales_returns(self):
        self.open_window("sales_returns", SalesReturnsWindow)

    def open_purchases(self):
        self.open_window("purchases", PurchasesWindow)

    def open_purchase_workflow(self):
        self.open_window("purchase_workflow", PurchaseWorkflowWindow)

    def open_purchase_returns(self):
        self.open_window("purchase_returns", PurchaseReturnsWindow)

    def open_parties(self):
        self.open_window("parties", PartiesWindow)

    def open_reports(self):
        self.open_window("reports", ReportsWindow)

    def open_accounting(self):
        self.open_window("accounting", accounting_window)

    def open_treasury(self):
        self.open_window("treasury", treasury_window)

    def open_treasury_accounts(self):
        self.open_window("treasury_accounts", TreasuryAccountsWindow)

    def open_employees(self):
        self.open_window("employees", employees_window)

    def open_settings(self):
        self.open_window("settings", settings_window)

    def open_enterprise_tools(self):
        self.open_window("enterprise_tools", EnterpriseToolsWindow)

    def open_backup(self):
        self.open_window("backup", BackupWindow)

    def open_health(self):
        self.open_window("health", HealthWindow)

    def create_backup(self):
        try:
            path = BackupService.create_backup()
            QMessageBox.information(
                self,
                "النسخ الاحتياطي",
                f"تم إنشاء نسخة احتياطية سليمة بنجاح:\\n{path}",
            )
        except Exception as exc:
            QMessageBox.critical(self, "فشل النسخ الاحتياطي", str(exc))

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

    login = LoginDialog()
    if login.exec() != QDialog.Accepted:
        return 0

    window = MainWindow()
    username = login.user.get("username", "admin") if login.user else "admin"
    window.setWindowTitle(f"{APP_NAME} - {APP_VERSION} | المستخدم: {username}")
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
