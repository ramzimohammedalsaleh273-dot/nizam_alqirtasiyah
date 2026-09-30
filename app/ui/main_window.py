from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QMessageBox, QDialog,
    QLineEdit, QDialogButtonBox, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from app.core.config import APP_NAME, APP_VERSION
from app.services.security_service import SecurityService
from app.services.system_service import get_system_summary, get_financial_summary, get_health
from app.ui.pos_window import POSWindow
from app.ui.sales_window import SalesWindow
from app.ui.purchases_window import PurchasesWindow
from app.ui.parties_window import PartiesWindow
from app.ui.inventory_window import InventoryWindow
from app.ui.reports_window import ReportsWindow
from app.ui.administration_windows import accounting_window, treasury_window, employees_window, settings_window
from app.ui.health_window import HealthWindow
from app.ui.backup_window import BackupWindow
from app.ui.enterprise_tools_window import EnterpriseToolsWindow
from app.ui.purchase_workflow_window import PurchaseWorkflowWindow
from app.ui.purchase_returns_window import PurchaseReturnsWindow
from app.ui.universal_search_window import UniversalSearchWindow
from app.ui.sales_returns_window import SalesReturnsWindow
from app.ui.treasury_accounts_window import TreasuryAccountsWindow
from app.ui.smart_operations_window import SmartOperationsWindow
from app.database.connection import get_session
from app.services.treasury_schema_service import TreasurySchemaService


class LoginDialog(QDialog):
    """بوابة دخول قبل فتح النظام."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.user = None
        self.security = SecurityService()
        self.setWindowTitle("تسجيل الدخول — نظام القرطاسية")
        self.setFixedSize(440, 310)
        self.setLayoutDirection(Qt.RightToLeft)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)

        title = QLabel("نظام القرطاسية")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:26px;font-weight:700;padding:8px;")
        layout.addWidget(title)

        subtitle = QLabel("تسجيل الدخول إلى بيئة التشغيل")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color:#9FB2C8;padding-bottom:8px;")
        layout.addWidget(subtitle)

        self.username = QLineEdit()
        self.username.setPlaceholderText("اسم المستخدم")
        self.username.setMinimumHeight(42)
        layout.addWidget(self.username)

        self.password = QLineEdit()
        self.password.setPlaceholderText("كلمة المرور")
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setMinimumHeight(42)
        layout.addWidget(self.password)

        self.message = QLabel("")
        self.message.setAlignment(Qt.AlignCenter)
        self.message.setWordWrap(True)
        layout.addWidget(self.message)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
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
    """الحاوية الرئيسية: تنقل منظم ومحتوى واسع بدل تكديس الوحدات."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} - {APP_VERSION}")
        self.setMinimumSize(1180, 720)
        self._child_windows = {}
        self._bootstrap_operational_schema()
        self.build_ui()

    def _bootstrap_operational_schema(self):
        with get_session() as session:
            TreasurySchemaService.ensure(session)
            session.commit()

    def build_ui(self):
        self.setStyleSheet("""
            QMainWindow, QWidget#Root { background:#07111F; }
            QLabel { color:#F4F7FB; }
            QFrame#Sidebar {
                background:#0B1728;
                border:1px solid #1A3049;
                border-radius:16px;
            }
            QFrame#BrandCard {
                background:#10243A;
                border:1px solid #234361;
                border-radius:14px;
            }
            QFrame#Section {
                background:#0E1C2D;
                border:1px solid #1A3049;
                border-radius:12px;
            }
            QFrame#Card {
                background:#101F33;
                border:1px solid #1E3856;
                border-radius:14px;
            }
            QFrame#StatusCard {
                background:#0E1C2D;
                border:1px solid #244566;
                border-radius:12px;
            }
            QPushButton {
                background:#13263D;
                color:#F4F7FB;
                border:1px solid #244566;
                border-radius:9px;
                padding:9px 12px;
                min-height:20px;
            }
            QPushButton:hover { background:#183452; }
            QPushButton:pressed { background:#0F2034; }
            QScrollArea { border:none; background:transparent; }
            QLineEdit {
                background:#0E1C2D;
                color:#F4F7FB;
                border:1px solid #28445F;
                border-radius:9px;
                padding:10px;
            }
        """)

        root = QWidget()
        root.setObjectName("Root")
        main = QHBoxLayout(root)
        main.setContentsMargins(14, 14, 14, 14)
        main.setSpacing(14)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(270)
        side_outer = QVBoxLayout(sidebar)
        side_outer.setContentsMargins(10, 10, 10, 10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        side_content = QWidget()
        side_layout = QVBoxLayout(side_content)
        side_layout.setContentsMargins(4, 4, 4, 4)
        side_layout.setSpacing(8)

        brand = QFrame()
        brand.setObjectName("BrandCard")
        brand_layout = QVBoxLayout(brand)

        logo = QLabel("نظام القرطاسية")
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet("font-size:21px;font-weight:700;padding:7px;")
        brand_layout.addWidget(logo)

        version = QLabel(f"الإصدار {APP_VERSION}")
        version.setAlignment(Qt.AlignCenter)
        version.setStyleSheet("color:#9FB2C8;font-size:12px;")
        brand_layout.addWidget(version)
        side_layout.addWidget(brand)

        search_button = QPushButton("⌕  البحث العام 360°")
        search_button.setMinimumHeight(42)
        search_button.clicked.connect(self.open_universal_search)
        side_layout.addWidget(search_button)

        quick_button = QPushButton("⚡  مركز التشغيل الذكي")
        quick_button.setMinimumHeight(42)
        quick_button.clicked.connect(self.open_smart_operations)
        side_layout.addWidget(quick_button)

        groups = [
            ("التشغيل اليومي", [
                ("لوحة التحكم", self.show_dashboard),
                ("نقطة البيع", self.open_pos),
                ("المبيعات والفواتير", self.open_sales),
                ("مرتجعات المبيعات", self.open_sales_returns),
            ]),
            ("المشتريات", [
                ("المشتريات", self.open_purchases),
                ("دورة المشتريات", self.open_purchase_workflow),
                ("مرتجعات المشتريات", self.open_purchase_returns),
            ]),
            ("المخزون والأطراف", [
                ("المنتجات والمخزون", self.open_inventory),
                ("العملاء والموردون", self.open_parties),
            ]),
            ("المالية", [
                ("الخزينة والبنوك", self.open_treasury),
                ("حسابات الخزينة والتحويلات", self.open_treasury_accounts),
                ("المحاسبة العامة", self.open_accounting),
                ("التقارير والتحليلات", self.open_reports),
            ]),
            ("الإدارة والرقابة", [
                ("الموظفون", self.open_employees),
                ("الإعدادات", self.open_settings),
                ("مركز التشغيل والفحص", self.open_enterprise_tools),
                ("صحة النظام", self.open_health),
                ("النسخ الاحتياطي", self.open_backup),
            ]),
        ]

        for section_name, actions in groups:
            section = QFrame()
            section.setObjectName("Section")
            section_layout = QVBoxLayout(section)
            section_layout.setContentsMargins(8, 8, 8, 8)
            section_layout.setSpacing(5)

            header = QLabel(section_name)
            header.setStyleSheet(
                "color:#8FA8C0;font-size:12px;font-weight:700;padding:3px 6px;"
            )
            section_layout.addWidget(header)

            for label, handler in actions:
                button = QPushButton(label)
                button.setMinimumHeight(38)
                button.clicked.connect(handler)
                section_layout.addWidget(button)

            side_layout.addWidget(section)

        side_layout.addStretch()
        scroll.setWidget(side_content)
        side_outer.addWidget(scroll)
        main.addWidget(sidebar)

        self.content = QFrame()
        self.content.setObjectName("Content")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(4, 4, 4, 4)
        main.addWidget(self.content, 1)

        self.setCentralWidget(root)

        shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
        shortcut.activated.connect(self.open_universal_search)
        self._global_search_shortcut = shortcut

        self.show_dashboard()

    def clear_content(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _add_summary_card(self, layout, row, column, title, value):
        card = QFrame()
        card.setObjectName("Card")
        card.setMinimumHeight(112)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(5)

        label = QLabel(title)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color:#9FB2C8;font-size:13px;")

        number = QLabel(f"{value:,}" if isinstance(value, int) else str(value))
        number.setAlignment(Qt.AlignCenter)
        number.setStyleSheet("font-size:25px;font-weight:700;padding:3px;")

        card_layout.addWidget(label)
        card_layout.addWidget(number)
        layout.addWidget(card, row, column)

    def _add_financial_card(self, layout, row, column, title, value):
        card = QFrame()
        card.setObjectName("StatusCard")
        card.setMinimumHeight(86)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 10)

        label = QLabel(title)
        label.setStyleSheet("color:#9FB2C8;font-size:12px;")
        value_label = QLabel(f"{float(value or 0):,.2f}")
        value_label.setStyleSheet("font-size:18px;font-weight:700;")

        card_layout.addWidget(label)
        card_layout.addWidget(value_label)
        layout.addWidget(card, row, column)

    def show_dashboard(self):
        self.clear_content()

        header = QHBoxLayout()
        title_box = QVBoxLayout()

        title = QLabel("لوحة التحكم")
        title.setStyleSheet("font-size:30px;font-weight:700;")
        subtitle = QLabel("ملخص تشغيلي سريع — التفاصيل الكاملة داخل كل وحدة")
        subtitle.setStyleSheet("color:#9FB2C8;font-size:13px;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        header.addLayout(title_box)
        header.addStretch()

        refresh = QPushButton("تحديث اللوحة")
        refresh.setMinimumHeight(40)
        refresh.clicked.connect(self.show_dashboard)
        header.addWidget(refresh)
        self.content_layout.addLayout(header)

        try:
            health = get_health()
            summary = get_system_summary()
            financial = get_financial_summary()

            status = QFrame()
            status.setObjectName("StatusCard")
            status_layout = QHBoxLayout(status)
            status_layout.setContentsMargins(14, 10, 14, 10)

            status_text = QLabel(
                "● قاعدة البيانات سليمة"
                if health["healthy"]
                else "● توجد مشكلة تحتاج إلى مراجعة"
            )
            status_text.setStyleSheet("font-size:15px;font-weight:700;")
            status_layout.addWidget(status_text)

            hint = QLabel("اللوحة تعرض المؤشرات فقط؛ لا يتم حشر تفاصيل السجلات هنا.")
            hint.setStyleSheet("color:#9FB2C8;")
            status_layout.addStretch()
            status_layout.addWidget(hint)
            self.content_layout.addWidget(status)

            cards = QGridLayout()
            cards.setHorizontalSpacing(12)
            cards.setVerticalSpacing(12)
            cards.setColumnStretch(0, 1)
            cards.setColumnStretch(1, 1)
            cards.setColumnStretch(2, 1)
            cards.setColumnStretch(3, 1)

            data = [
                ("المنتجات", summary["products"]),
                ("العملاء", summary["customers"]),
                ("الموردون", summary["suppliers"]),
                ("فواتير المبيعات", summary["sales"]),
                ("فواتير المشتريات", summary["purchase_invoices"]),
                ("أرصدة المخزون", summary["stock"]),
                ("أصناف منخفضة", summary["low_stock"]),
            ]
            for index, (name, value) in enumerate(data):
                row, column = divmod(index, 4)
                self._add_summary_card(cards, row, column, name, value)

            self.content_layout.addLayout(cards)

            financial_title = QLabel("الملخص المالي")
            financial_title.setStyleSheet("font-size:18px;font-weight:700;padding-top:8px;")
            self.content_layout.addWidget(financial_title)

            financial_grid = QGridLayout()
            financial_grid.setHorizontalSpacing(12)
            financial_grid.setVerticalSpacing(10)
            for column in range(4):
                financial_grid.setColumnStretch(column, 1)

            self._add_financial_card(financial_grid, 0, 0, "النقدية", financial["cash"])
            self._add_financial_card(financial_grid, 0, 1, "البنوك", financial["banks"])
            self._add_financial_card(financial_grid, 0, 2, "ذمم العملاء", financial["customers"])
            self._add_financial_card(financial_grid, 0, 3, "قيمة المخزون", financial["inventory"])

            self.content_layout.addLayout(financial_grid)

        except Exception as exc:
            QMessageBox.critical(self, "خطأ في لوحة التحكم", str(exc))

        self.content_layout.addStretch()

    def open_window(self, key, window_class):
        window = self._child_windows.get(key)
        if window is None:
            window = window_class()
            self._child_windows[key] = window
        window.show()
        window.raise_()
        window.activateWindow()

    def open_universal_search(self):
        self.open_window("universal_search", UniversalSearchWindow)

    def open_smart_operations(self):
        self.open_window("smart_operations", SmartOperationsWindow)

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
