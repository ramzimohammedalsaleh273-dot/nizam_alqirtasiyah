from pathlib import Path
from datetime import datetime
import shutil
import ast
import sys

ROOT = Path.cwd()
MAIN = ROOT / "app" / "ui" / "main_window.py"
SERVICE = ROOT / "app" / "services" / "pos_search_service.py"
DB = ROOT / "database" / "nizam_alqirtasiyah.db"
BACKUPS = ROOT / "backups"

print("=" * 80)
print("ROBUST POS SEARCH UI PATCH")
print("=" * 80)

if not MAIN.exists():
    raise SystemExit("ERROR: main_window.py غير موجود")

if not SERVICE.exists():
    raise SystemExit("ERROR: pos_search_service.py غير موجود")

BACKUPS.mkdir(exist_ok=True)

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BACKUPS / f"before_robust_pos_ui_{stamp}.py"
shutil.copy2(MAIN, backup)

print("BACKUP:", backup)

source = MAIN.read_text(encoding="utf-8")

# =========================================================
# تحليل الملف الأصلي
# =========================================================
try:
    tree = ast.parse(source)
except Exception as e:
    raise SystemExit(f"ERROR: main_window.py الأصلي غير صالح: {e}")

print("ORIGINAL SYNTAX: OK")

# =========================================================
# اختبار خدمة البحث أولاً
# =========================================================
sys.path.insert(0, str(ROOT))

try:
    from app.services.pos_search_service import POSProductSearch

    searcher = POSProductSearch()

    print("-" * 80)
    print("SEARCH SERVICE")

    for q in ["1", "PEN-001", "قلم", "دفتر", "628000000001"]:
        result = searcher.search(q)
        print(f"{q}: {result[:2]}")

    print("SEARCH SERVICE: OK")

except Exception as e:
    raise SystemExit(f"ERROR: خدمة البحث لا تعمل: {e}")

# =========================================================
# منع تكرار الاستيراد
# =========================================================
import_line = "from app.services.pos_search_service import POSProductSearch"

lines = source.splitlines(True)

if import_line not in source:
    # نضع الاستيراد بعد:
    # 1. docstring إن وجد
    # 2. from __future__
    # 3. بقية imports
    #
    # أسهل وأأمن مكان: بعد آخر import في أول جزء من الملف
    insert_line = 0

    # تخطي docstring
    if tree.body and isinstance(tree.body[0], ast.Expr):
        node = tree.body[0]
        if isinstance(node.value, (ast.Constant, ast.Str)):
            insert_line = node.end_lineno

    # تخطي future imports
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "__future__":
            insert_line = max(insert_line, node.end_lineno)

    # ضع الاستيراد بعد جميع الاستيرادات الموجودة في رأس الملف
    last_import = insert_line

    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            last_import = max(last_import, node.end_lineno)

    lines.insert(last_import, import_line + "\n")
    source = "".join(lines)

    print("IMPORT: ADDED")
else:
    print("IMPORT: ALREADY EXISTS")

# =========================================================
# إعادة تحليل الملف بعد الاستيراد
# =========================================================
tree = ast.parse(source)

# =========================================================
# البحث عن أول class رئيسية
# =========================================================
classes = [
    node for node in tree.body
    if isinstance(node, ast.ClassDef)
]

if not classes:
    shutil.copy2(backup, MAIN)
    raise SystemExit("ERROR: لم يتم العثور على class رئيسية في main_window.py")

main_class = classes[0]

print("MAIN CLASS:", main_class.name)

# =========================================================
# إزالة أي نسخة سابقة من دالة البحث
# =========================================================
method_name = "search_pos_products"

# نحدد الأسطر التي تحتوي الدالة داخل الـ class
old_method = None

for node in main_class.body:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        if node.name == method_name:
            old_method = node
            break

if old_method:
    start = old_method.lineno - 1
    end = old_method.end_lineno

    current_lines = source.splitlines(True)

    del current_lines[start:end]

    source = "".join(current_lines)

    print("OLD POS SEARCH METHOD: REMOVED")

    tree = ast.parse(source)

    classes = [
        node for node in tree.body
        if isinstance(node, ast.ClassDef)
    ]

    main_class = classes[0]

# =========================================================
# إنشاء الدالة الصحيحة
# =========================================================
method_code = '''
    def search_pos_products(self, text):
        """بحث POS بالرقم أو SKU أو الاسم أو الباركود."""
        try:
            query = str(text or "").strip()

            if not query:
                return []

            searcher = POSProductSearch()
            return searcher.search(query) or []

        except Exception as exc:
            print("POS SEARCH ERROR:", exc)
            return []
'''

# =========================================================
# تحديد نهاية class بدقة
# =========================================================
source_lines = source.splitlines(True)

class_end = main_class.end_lineno

# إذا كانت هناك عناصر أخرى داخل الملف بعد الـ class،
# نضع الدالة قبل نهاية الـ class مباشرة.
insert_index = class_end

# تعديل إذا كانت نهاية class تغيّرت بسبب الأسطر
source_lines.insert(insert_index, method_code)

patched = "".join(source_lines)

# =========================================================
# فحص الصياغة قبل الكتابة
# =========================================================
try:
    ast.parse(patched)
    print("PATCHED SYNTAX: OK")
except Exception as e:
    shutil.copy2(backup, MAIN)
    raise SystemExit(f"PATCH FAILED - ORIGINAL RESTORED: {e}")

# =========================================================
# الكتابة
# =========================================================
MAIN.write_text(patched, encoding="utf-8")

# =========================================================
# فحص نهائي من الملف نفسه
# =========================================================
try:
    final_source = MAIN.read_text(encoding="utf-8")
    final_tree = ast.parse(final_source)

    found_import = import_line in final_source
    found_method = "def search_pos_products(self, text):" in final_source

    if not found_import:
        raise RuntimeError("الاستيراد غير موجود بعد الحفظ")

    if not found_method:
        raise RuntimeError("دالة البحث غير موجودة بعد الحفظ")

    print("FINAL SYNTAX: OK")
    print("IMPORT: OK")
    print("POS SEARCH METHOD: OK")

except Exception as e:
    shutil.copy2(backup, MAIN)
    raise SystemExit(f"FINAL CHECK FAILED - RESTORED: {e}")

print("=" * 80)
print("STATUS: SUCCESS")
print("POS SEARCH UI CONNECTION INSTALLED")
print("=" * 80)
