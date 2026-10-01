from datetime import datetime
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QMessageBox, QDialog,
    QLineEdit, QDialogButtonBox, QScrollArea, QSizePolicy,
    QTableWidget, QTableWidgetItem, QAbstractItemView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from sqlalchemy import text
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
from app.ui.theme import APP_STYLE
from app.ui.access_data_window import AccessDataWindow


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
        self.setStyleSheet(APP_STYLE)

        root = QWidget()
        root.setObjectName("Root")
        main = QVBoxLayout(root)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        top = QFrame()
        top.setObjectName("TopBar")
        tl = QHBoxLayout(top)
        tl.setContentsMargins(18, 10, 18, 10)
        tl.setSpacing(14)

        title = QLabel("نظام القرطاسية")
        title.setObjectName("TopTitle")
        tl.addWidget(title)

        badge = QFrame()
        badge.setObjectName("Badge")
        bl = QHBoxLayout(badge)
        bl.setContentsMargins(10, 4, 10, 4)
        btxt = QLabel("● يعمل محليًا")
        btxt.setStyleSheet("color:#f8fafc;font-size:12px;")
        bl.addWidget(btxt)
        tl.addWidget(badge)
        tl.addStretch()

        self.user_meta = QLabel("المستخدم: —")
        self.user_meta.setObjectName("TopMeta")
        self.branch_meta = QLabel("الفرع: —")
        self.branch_meta.setObjectName("TopMeta")
        self.datetime_meta = QLabel()
        self.datetime_meta.setObjectName("TopMeta")
        self.db_meta = QLabel("قاعدة البيانات: —")
        self.db_meta.setObjectName("TopMeta")
        for w in (self.user_meta, self.branch_meta, self.datetime_meta, self.db_meta):
            tl.addWidget(w)
        main.addWidget(top)

        nav = QFrame()
        nav.setObjectName("NavBar")
        nl = QHBoxLayout(nav)
        nl.setContentsMargins(10, 0, 10, 0)
        nl.setSpacing(0)
        self._nav_buttons = {}
        for label, handler in [
            ("الرئيسية", self.show_dashboard),
            ("المبيعات", self.open_sales),
            ("المشتريات", self.open_purchases),
            ("المخزون", self.open_inventory),
            ("العملاء", lambda: self.open_data("customers", "العملاء")),
            ("الموردون", lambda: self.open_data("suppliers", "الموردون")),
            ("المالية", self.open_treasury),
            ("المحاسبة", self.open_accounting),
            ("التقارير", self.open_reports),
            ("الإعدادات", self.open_settings),
            ("أدوات", self.open_enterprise_tools),
        ]:
            b = QPushButton(label)
            b.setObjectName("NavButton")
            b.setCheckable(True)
            b.clicked.connect(handler)
            nl.addWidget(b)
            self._nav_buttons[label] = b
        main.addWidget(nav)

        work = QHBoxLayout()
        work.setContentsMargins(10, 10, 10, 10)
        work.setSpacing(10)

        sidebar = QFrame()
        sidebar.setObjectName("SideBar")
        sidebar.setFixedWidth(255)
        so = QVBoxLayout(sidebar)
        so.setContentsMargins(8, 8, 8, 8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        sc = QWidget()
        sl = QVBoxLayout(sc)
        sl.setContentsMargins(2, 2, 2, 2)
        sl.setSpacing(8)

        quick = QFrame()
        quick.setObjectName("SideSection")
        ql = QVBoxLayout(quick)
        ql.setContentsMargins(6, 6, 6, 6)
        for label, handler in [
            ("⌕  البحث العام", self.open_universal_search),
            ("▣  نقطة البيع", self.open_pos),
        ]:
            b = QPushButton(label)
            b.setObjectName("SideButton")
            b.clicked.connect(handler)
            ql.addWidget(b)
        sl.addWidget(quick)

        groups = [
            ("التشغيل", [
                ("لوحة التحكم", self.show_dashboard),
                ("المبيعات والفواتير", self.open_sales),
                ("مرتجعات المبيعات", self.open_sales_returns),
            ]),
            ("المشتريات", [
                ("المشتريات", self.open_purchases),
                ("دورة المشتريات", self.open_purchase_workflow),
                ("مرتجعات المشتريات", self.open_purchase_returns),
            ]),
            ("المخزون والأطراف", [
                ("المنتجات", lambda: self.open_data("products", "المنتجات")),
                ("التصنيفات", lambda: self.open_data("product_categories", "التصنيفات")),
                ("الوحدات", lambda: self.open_data("units", "الوحدات")),
                ("المستودعات", lambda: self.open_data("warehouses", "المستودعات")),
                ("المخزون وحركاته", self.open_inventory),
                ("الجرد", lambda: self.open_data("stocktakes", "الجرد")),
                ("العملاء", lambda: self.open_data("customers", "العملاء")),
                ("الموردون", lambda: self.open_data("suppliers", "الموردون")),
            ]),
            ("المالية", [
                ("الخزينة", self.open_treasury),
                ("البنوك والحسابات", self.open_treasury_accounts),
                ("المحاسبة العامة", self.open_accounting),
                ("دليل الحسابات", lambda: self.open_data("accounts", "دليل الحسابات")),
                ("الصناديق", lambda: self.open_data("cash_registers", "الصناديق")),
                ("الضرائب", lambda: self.open_data("tax_rates", "الضرائب")),
                ("الفترات المالية", lambda: self.open_data("fiscal_periods", "الفترات المالية")),
            ]),
            ("الإدارة والرقابة", [
                ("الشركات", lambda: self.open_data("companies", "الشركات")),
                ("الفروع", lambda: self.open_data("branches", "الفروع")),
                ("الموظفون", lambda: self.open_data("employees", "الموظفون")),
                ("المستخدمون", lambda: self.open_data("users", "المستخدمون")),
                ("الأدوار والصلاحيات", lambda: self.open_data("roles", "الأدوار")),
                ("التقارير والتحليلات", self.open_reports),
                ("التنبيهات", self.open_smart_operations),
                ("المستندات", lambda: self.open_data("documents", "المستندات")),
                ("سجل التدقيق", lambda: self.open_data("audit_logs", "سجل التدقيق", editable=False)),
                ("المزامنة", lambda: self.open_data("sync_queue", "طابور المزامنة", editable=False)),
                ("النسخ الاحتياطي", self.open_backup),
                ("الإعدادات", self.open_settings),
                ("صحة النظام", self.open_health),
            ]),
        ]
        for name, actions in groups:
            sec = QFrame()
            sec.setObjectName("SideSection")
            vl = QVBoxLayout(sec)
            vl.setContentsMargins(6, 6, 6, 6)
            head = QLabel(name)
            head.setObjectName("SideSectionTitle")
            vl.addWidget(head)
            for label, handler in actions:
                b = QPushButton(label)
                b.setObjectName("SideButton")
                b.clicked.connect(handler)
                vl.addWidget(b)
            sl.addWidget(sec)
        sl.addStretch()
        scroll.setWidget(sc)
        so.addWidget(scroll)
        work.addWidget(sidebar)

        self.content = QFrame()
        self.content.setObjectName("Card")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(14, 14, 14, 14)
        self.content_layout.setSpacing(10)
        work.addWidget(self.content, 1)
        main.addLayout(work, 1)

        self.status_bar = self.statusBar()
        self.status_bar.showMessage("جاهز")
        self.setCentralWidget(root)

        shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
        shortcut.activated.connect(self.open_universal_search)
        self._global_search_shortcut = shortcut
        self._set_datetime()
        self.show_dashboard()

    def _set_datetime(self):
        self.datetime_meta.setText(datetime.now().strftime("%Y-%m-%d  %H:%M"))

    def _set_active_nav(self, label):
        for name, button in self._nav_buttons.items():
            button.setChecked(name == label)

    def clear_content(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    @staticmethod
    def _make_table(headers, rows, minimum_height=190):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setMinimumHeight(minimum_height)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setStretchLastSection(True)
        for values in rows:
            r = table.rowCount()
            table.insertRow(r)
            for col, value in enumerate(values):
                table.setItem(r, col, QTableWidgetItem("" if value is None else str(value)))
        return table

    @staticmethod
    def _preview_table(session, table_name, preferred_columns, limit=8):
        try:
            columns = [row[1] for row in session.execute(text(f'PRAGMA table_info("{table_name}")')).all()]
            selected = [x for x in preferred_columns if x in columns]
            if not selected:
                return []
            fields = ", ".join(f'"{x}"' for x in selected)
            rows = session.execute(
                text(f'SELECT {fields} FROM "{table_name}" ORDER BY rowid DESC LIMIT :limit'),
                {"limit": limit},
            ).all()
            return [tuple(row) for row in rows]
        except Exception:
            return []

    def _dashboard_section(self, title, headers, rows):
        frame = QFrame()
        frame.setObjectName("Card")
        layout = QVBoxLayout(frame)
        label = QLabel(title)
        label.setStyleSheet("font-size:16px;font-weight:700;color:#0f172a;")
        layout.addWidget(label)
        layout.addWidget(self._make_table(headers, rows))
        return frame

    def show_dashboard(self):
        self.clear_content()
        self._set_active_nav("الرئيسية")

        head = QHBoxLayout()
        box = QVBoxLayout()
        title = QLabel("لوحة التحكم")
        title.setObjectName("SectionTitle")
        sub = QLabel("بيانات تشغيلية وجداول فعلية — بدون تكديس بطاقات كبيرة.")
        sub.setObjectName("SectionSubTitle")
        box.addWidget(title)
        box.addWidget(sub)
        head.addLayout(box)
        head.addStretch()
        refresh = QPushButton("تحديث")
        refresh.setObjectName("Primary")
        refresh.clicked.connect(self.show_dashboard)
        head.addWidget(refresh)
        self.content_layout.addLayout(head)

        try:
            health = get_health()
            summary = get_system_summary()
            financial = get_financial_summary()
            self.db_meta.setText(
                "قاعدة البيانات: سليمة" if health["healthy"] else "قاعدة البيانات: تحتاج مراجعة"
            )

            info = QFrame()
            info.setObjectName("Card")
            il = QHBoxLayout(info)
            il.setContentsMargins(12, 8, 12, 8)
            data = [
                ("المستخدم", getattr(self, "current_user", {}).get("username", "—")),
                ("الفرع", getattr(self, "current_user", {}).get("branch_name", "—")),
                ("التاريخ", datetime.now().strftime("%Y-%m-%d")),
                ("الوقت", datetime.now().strftime("%H:%M")),
                ("الحالة", "سليم" if health["healthy"] else "مراجعة"),
            ]
            for name, value in data:
                b = QVBoxLayout()
                a = QLabel(name)
                a.setStyleSheet("color:#64748b;font-size:11px;")
                v = QLabel(str(value))
                v.setStyleSheet("font-weight:700;color:#0f172a;")
                b.addWidget(a)
                b.addWidget(v)
                il.addLayout(b)
            self.content_layout.addWidget(info)

            metrics = QFrame()
            metrics.setObjectName("Card")
            ml = QHBoxLayout(metrics)
            for name, value in [
                ("المنتجات", summary["products"]),
                ("العملاء", summary["customers"]),
                ("الموردون", summary["suppliers"]),
                ("المبيعات", summary["sales"]),
                ("المشتريات", summary["purchase_invoices"]),
                ("أصناف منخفضة", summary["low_stock"]),
                ("قيمة المخزون", f'{financial["inventory"]:,.2f}'),
            ]:
                b = QVBoxLayout()
                a = QLabel(name)
                a.setStyleSheet("color:#64748b;font-size:11px;")
                v = QLabel(f"{value:,}" if isinstance(value, int) else str(value))
                v.setStyleSheet("font-size:17px;font-weight:700;color:#0f172a;")
                b.addWidget(a)
                b.addWidget(v)
                ml.addLayout(b)
            self.content_layout.addWidget(metrics)

            with get_session() as session:
                sales = self._preview_table(
                    session, "sales",
                    ["invoice_number", "invoice_date", "customer_id", "total", "payment_method", "status"],
                )
                purchases = self._preview_table(
                    session, "purchase_invoices",
                    ["invoice_number", "invoice_date", "supplier_id", "total", "status"],
                )
                alerts = self._preview_table(
                    session, "notifications",
                    ["type", "title", "message", "created_at", "status"],
                )
                low = session.execute(text("""
                    SELECT p.barcode, p.name_ar,
                           COALESCE(st.available_quantity,0),
                           COALESCE(NULLIF(p.reorder_point,0),p.min_stock,0)
                    FROM products p
                    LEFT JOIN stock st ON st.product_id=p.id
                    WHERE p.is_active=1
                      AND COALESCE(st.available_quantity,0)
                          <= COALESCE(NULLIF(p.reorder_point,0),p.min_stock,0)
                    ORDER BY COALESCE(st.available_quantity,0), p.name_ar
                    LIMIT 8
                """)).all()

            top = QHBoxLayout()
            top.addWidget(self._dashboard_section(
                "آخر المبيعات",
                ["رقم الفاتورة", "التاريخ", "العميل", "الإجمالي", "طريقة الدفع", "الحالة"],
                sales,
            ), 1)
            top.addWidget(self._dashboard_section(
                "آخر المشتريات",
                ["رقم الفاتورة", "التاريخ", "المورد", "الإجمالي", "الحالة"],
                purchases,
            ), 1)
            self.content_layout.addLayout(top)

            bottom = QHBoxLayout()
            bottom.addWidget(self._dashboard_section(
                "التنبيهات",
                ["النوع", "العنوان", "التفاصيل", "التاريخ", "الحالة"],
                alerts,
            ), 1)
            bottom.addWidget(self._dashboard_section(
                "الأصناف منخفضة المخزون",
                ["الباركود", "الصنف", "الرصيد الحالي", "الحد الأدنى"],
                low,
            ), 1)
            self.content_layout.addLayout(bottom)

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

    def open_data(self, table_name, title=None, columns=None, editable=True):
        key = "data:" + table_name
        window = self._child_windows.get(key)
        if window is None:
            window = AccessDataWindow(table_name, title, columns, editable=editable)
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
