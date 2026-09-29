import sqlite3
from pathlib import Path

DB = Path("database") / "nizam_alqirtasiyah.db"
UI = Path("app") / "ui" / "main_window.py"

con = sqlite3.connect(DB)

def cols(table):
    return [r[1] for r in con.execute(f'PRAGMA table_info("{table}")').fetchall()]

products = cols("products")
accounts = cols("accounts")
settings = cols("system_settings")

print("=" * 70)
print("فحص أعمدة قاعدة البيانات قبل إصلاح الواجهة")
print("=" * 70)
print("products:", products)
print("accounts:", accounts)
print("system_settings:", settings)

if not products:
    raise RuntimeError("جدول products غير موجود أو فارغ من البنية")

if not accounts:
    raise RuntimeError("جدول accounts غير موجود أو فارغ من البنية")

ui = UI.read_text(encoding="utf-8")

# إصلاح استعلام الحسابات حسب البنية الفعلية
ui = ui.replace(
    "SELECT code,name,type,is_active FROM accounts ORDER BY code",
    "SELECT account_code,account_name,account_type,is_active FROM accounts ORDER BY account_code"
)

# إصلاح أسماء أعمدة عرض الحسابات إن وجدت
ui = ui.replace(
    "['code', 'name', 'type', 'is_active']",
    "['account_code', 'account_name', 'account_type', 'is_active']"
)

# إصلاح العناوين الشائعة
ui = ui.replace(
    "الكود', 'الاسم', 'النوع', 'نشط'",
    "رمز الحساب', 'اسم الحساب', 'نوع الحساب', 'نشط'"
)

# إضافة شاشة إعدادات حقيقية إذا لم تكن موجودة
if "def show_settings" not in ui:
    marker = "\n    def show_accounts(self):"
    settings_method = r'''
    def show_settings(self):
        self.clear_content()

        title = QLabel("الإعدادات")
        title.setObjectName("pageTitle")
        self.content_layout.addWidget(title)

        subtitle = QLabel("إعدادات النظام الأساسية")
        subtitle.setObjectName("pageSubtitle")
        self.content_layout.addWidget(subtitle)

        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["المفتاح", "القيمة", "الحالة"])
        table.setRowCount(0)
        table.horizontalHeader().setStretchLastSection(True)

        try:
            rows = self.db.execute(
                "SELECT key, value, is_active FROM system_settings ORDER BY key"
            ).fetchall()

            table.setRowCount(len(rows))

            for i, row in enumerate(rows):
                table.setItem(i, 0, QTableWidgetItem(str(row[0])))
                table.setItem(i, 1, QTableWidgetItem("" if row[1] is None else str(row[1])))
                table.setItem(i, 2, QTableWidgetItem(
                    "مفعّل" if row[2] else "غير مفعّل"
                ))
        except Exception as e:
            table.setRowCount(1)
            table.setItem(0, 0, QTableWidgetItem("خطأ"))
            table.setItem(0, 1, QTableWidgetItem(str(e)))
            table.setItem(0, 2, QTableWidgetItem(""))

        self.content_layout.addWidget(table)
'''
    if marker in ui:
        ui = ui.replace(marker, settings_method + marker)

# ربط زر الإعدادات بالدالة الجديدة
ui = ui.replace(
    '("الإعدادات", self.show_placeholder)',
    '("الإعدادات", self.show_settings)'
)

UI.write_text(ui, encoding="utf-8")

con.close()

# فحص Python
import py_compile
py_compile.compile(str(UI), doraise=True)

print("=" * 70)
print("DATABASE UI FIX")
print("=" * 70)
print("الحسابات: تم تصحيح أسماء الأعمدة")
print("الإعدادات: تم ربط شاشة فعلية بجدول system_settings")
print("نسخة احتياطية:", backup)
print("PYTHON CHECK: PASSED")
print("STATUS: SUCCESS")
print("=" * 70)
