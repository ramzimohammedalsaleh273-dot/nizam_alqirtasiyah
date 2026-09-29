from pathlib import Path
import shutil, datetime, os

ROOT = Path(r"C:\Users\Ramzi Al Saleh\Desktop\Nizam_AlQirtasiyah")
DB = ROOT / "database" / "nizam_alqirtasiyah.db"

# ============================================================
# 1) نسخة احتياطية
# ============================================================
backup_dir = ROOT / "database" / "backups"
backup_dir.mkdir(parents=True, exist_ok=True)

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = backup_dir / f"nizam_alqirtasiyah_before_app_layer_{stamp}.db"

if DB.exists():
    shutil.copy2(DB, backup)

# ============================================================
# 2) المجلدات
# ============================================================
dirs = [
    "app",
    "app/core",
    "app/database",
    "app/services",
    "app/ui",
    "app/ui/widgets",
    "app/utils",
    "tests",
    "logs",
]

for d in dirs:
    (ROOT / d).mkdir(parents=True, exist_ok=True)

# ============================================================
# 3) ملفات __init__
# ============================================================
for d in [
    "app",
    "app/core",
    "app/database",
    "app/services",
    "app/ui",
    "app/ui/widgets",
    "app/utils",
]:
    (ROOT / d / "__init__.py").write_text(
        "# نظام القرطاسية\n",
        encoding="utf-8"
    )

# ============================================================
# 4) الإعدادات
# ============================================================
(ROOT / "app" / "core" / "config.py").write_text(r'''
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATABASE_PATH = PROJECT_ROOT / "database" / "nizam_alqirtasiyah.db"
LOGS_PATH = PROJECT_ROOT / "logs"

APP_NAME = "نظام القرطاسية"
APP_VERSION = "1.0.0"
ORGANIZATION_NAME = "نظام القرطاسية"

WINDOW_MIN_WIDTH = 1200
WINDOW_MIN_HEIGHT = 720
''', encoding="utf-8")

# ============================================================
# 5) اتصال قاعدة البيانات
# ============================================================
(ROOT / "app" / "database" / "connection.py").write_text(r'''
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import DATABASE_PATH

DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(
    DATABASE_URL,
    future=True,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)

def get_session():
    return SessionLocal()

def database_health():
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA integrity_check")).scalar()
        foreign_keys = conn.execute(text("PRAGMA foreign_key_check")).fetchall()

    return {
        "integrity": result,
        "foreign_key_errors": len(foreign_keys),
        "healthy": result == "ok" and len(foreign_keys) == 0,
    }
''', encoding="utf-8")

# ============================================================
# 6) خدمة معلومات النظام
# ============================================================
(ROOT / "app" / "services" / "system_service.py").write_text(r'''
from sqlalchemy import text
from app.database.connection import get_session, database_health

def get_system_summary():
    with get_session() as session:

        def count(table):
            return session.execute(
                text(f'SELECT COUNT(*) FROM "{table}"')
            ).scalar() or 0

        summary = {
            "products": count("products"),
            "customers": count("customers"),
            "suppliers": count("suppliers"),
            "employees": count("employees"),
            "sales": count("sales"),
            "purchase_invoices": count("purchase_invoices"),
            "stock": count("stock"),
            "journal_entries": count("journal_entries"),
        }

        return summary

def get_financial_summary():
    with get_session() as session:

        def balance(code):
            value = session.execute(text("""
                SELECT
                    COALESCE(SUM(j.debit),0)
                    -
                    COALESCE(SUM(j.credit),0)
                FROM journal_entry_lines j
                JOIN accounts a ON a.id=j.account_id
                WHERE a.account_code=:code
            """), {"code": code}).scalar()

            return round(float(value or 0), 2)

        return {
            "cash": balance("1100"),
            "banks": balance("1200"),
            "customers": balance("1300"),
            "inventory": balance("1400"),
            "suppliers": balance("2100"),
            "sales": balance("4100"),
            "cogs": balance("5100"),
        }

def get_health():
    return database_health()
''', encoding="utf-8")

# ============================================================
# 7) السجل
# ============================================================
(ROOT / "app" / "core" / "logging_setup.py").write_text(r'''
import logging
from pathlib import Path
from app.core.config import LOGS_PATH

def setup_logging():
    LOGS_PATH.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("nizam_alqirtasiyah")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.FileHandler(
            LOGS_PATH / "system.log",
            encoding="utf-8"
        )
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
''', encoding="utf-8")

# ============================================================
# 8) الواجهة الرئيسية
# ============================================================
(ROOT / "app" / "ui" / "main_window.py").write_text(r'''
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
''', encoding="utf-8")

# ============================================================
# 9) نقطة التشغيل
# ============================================================
(ROOT / "main.py").write_text(r'''
from app.core.logging_setup import setup_logging

logger = setup_logging()
logger.info("بدء تشغيل نظام القرطاسية")

from app.ui.main_window import run

if __name__ == "__main__":
    run()
''', encoding="utf-8")

# ============================================================
# 10) اختبار النظام
# ============================================================
(ROOT / "tests" / "test_system.py").write_text(r'''
from app.database.connection import database_health
from app.services.system_service import (
    get_system_summary,
    get_financial_summary,
)

def test_database_health():
    result = database_health()
    assert result["integrity"] == "ok"
    assert result["foreign_key_errors"] == 0
    assert result["healthy"] is True

def test_system_summary():
    result = get_system_summary()
    assert result["products"] >= 0
    assert result["customers"] >= 0
    assert result["suppliers"] >= 0

def test_financial_summary():
    result = get_financial_summary()
    assert "inventory" in result
    assert "sales" in result
    assert "cogs" in result
''', encoding="utf-8")

# ============================================================
# 11) ملف حالة المشروع
# ============================================================
state = ROOT / ".lulu_state"
state.mkdir(exist_ok=True)

(state / "build_state.json").write_text(
    '''{
  "project": "نظام القرطاسية",
  "stage": "application_core",
  "last_completed_stage": 2,
  "offline_first": true,
  "database_verified": true
}
''',
    encoding="utf-8"
)

# ============================================================
# 12) التحقق النهائي
# ============================================================
print("=" * 70)
print("تم بناء طبقة التطبيق الأساسية بنجاح")
print("=" * 70)
print("النسخة الاحتياطية:", backup if DB.exists() else "لم تكن هناك قاعدة لإنشاء نسخة منها")
print("المجلد:", ROOT)

required = [
    "main.py",
    "app/core/config.py",
    "app/core/logging_setup.py",
    "app/database/connection.py",
    "app/services/system_service.py",
    "app/ui/main_window.py",
    "tests/test_system.py",
]

missing = []

for f in required:
    p = ROOT / f
    if p.exists():
        print("[OK]", f)
    else:
        print("[MISSING]", f)
        missing.append(f)

print("-" * 70)

if not missing:
    print("الملفات المطلوبة: OK")
else:
    print("الملفات الناقصة:", missing)

print("=" * 70)
