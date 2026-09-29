from pathlib import Path
from datetime import datetime
import shutil
import ast
import re

ROOT = Path.cwd()
MAIN = ROOT / "app" / "ui" / "main_window.py"
SERVICE = ROOT / "app" / "services" / "pos_search_service.py"
BACKUPS = ROOT / "backups"

print("=" * 80)
print("SAFE POS UI SEARCH CONNECTION")
print("=" * 80)

if not MAIN.exists():
    raise SystemExit("ERROR: main_window.py غير موجود")

if not SERVICE.exists():
    raise SystemExit("ERROR: pos_search_service.py غير موجود")

BACKUPS.mkdir(exist_ok=True)

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BACKUPS / f"before_safe_pos_ui_{stamp}.py"
shutil.copy2(MAIN, backup)
print("BACKUP:", backup)

original = MAIN.read_text(encoding="utf-8")

# ---------------------------------------------------------
# تحقق من أن الملف الأصلي سليم
# ---------------------------------------------------------
try:
    ast.parse(original)
    print("ORIGINAL SYNTAX: OK")
except Exception as e:
    raise SystemExit(f"ERROR: الملف الأصلي نفسه غير سليم: {e}")

text = original

# ---------------------------------------------------------
# إضافة الاستيراد في أعلى الملف، خارج أي class
# ---------------------------------------------------------
import_line = "from app.services.pos_search_service import POSProductSearch"

if import_line not in text:
    lines = text.splitlines(True)

    insert_at = 0

    # تخطّي shebang أو encoding أو docstring البسيط
    while insert_at < len(lines):
        s = lines[insert_at].strip()

        if (
            s.startswith("#!")
            or s.startswith("# -*-")
            or s.startswith("# coding")
            or s.startswith('"""')
            or s.startswith("'''")
            or s == ""
        ):
            insert_at += 1
        else:
            break

    lines.insert(insert_at, import_line + "\n")
    text = "".join(lines)

# ---------------------------------------------------------
# إضافة دالة بحث داخل class الرئيسية فقط
# ---------------------------------------------------------
if "def search_pos_products(self, text):" not in text:

    classes = list(re.finditer(
        r"^class\s+[A-Za-z_]\w*(?:\([^)]*\))?\s*:\s*$",
        text,
        re.MULTILINE
    ))

    if not classes:
        shutil.copy2(backup, MAIN)
        raise SystemExit("ERROR: لم يتم العثور على class داخل main_window.py")

    # نختار أول class رئيسية
    class_match = classes[0]
    class_start = class_match.end()

    method = '''
    def search_pos_products(self, text):
        """بحث منتجات POS بالرقم أو SKU أو الاسم أو الباركود."""
        try:
            query = str(text or "").strip()
            if not query:
                return []

            return POSProductSearch.search(query) or []

        except Exception as exc:
            print("POS SEARCH ERROR:", exc)
            return []
'''

    text = text[:class_start] + method + text[class_start:]

# ---------------------------------------------------------
# اختبار الصياغة قبل الحفظ
# ---------------------------------------------------------
try:
    ast.parse(text)
    print("PATCHED SYNTAX: OK")
except Exception as e:
    shutil.copy2(backup, MAIN)
    print("PATCH REJECTED: RESTORED BACKUP")
    raise SystemExit(f"SYNTAX ERROR: {e}")

# ---------------------------------------------------------
# حفظ التعديل
# ---------------------------------------------------------
MAIN.write_text(text, encoding="utf-8")
print("MAIN WINDOW: PATCHED SAFELY")

# ---------------------------------------------------------
# اختبار خدمة البحث
# ---------------------------------------------------------
import sys
sys.path.insert(0, str(ROOT))

try:
    from app.services.pos_search_service import POSProductSearch

    tests = ["1", "PEN-001", "قلم", "دفتر", "628000000001"]

    print("-" * 80)
    print("SEARCH SERVICE TEST")

    for q in tests:
        results = POSProductSearch.search(q)
        print(f"{q} -> {results[:3]}")

    print("SERVICE: OK")

except Exception as e:
    shutil.copy2(backup, MAIN)
    print("SERVICE FAILED: RESTORED BACKUP")
    raise SystemExit(f"SERVICE ERROR: {e}")

print("=" * 80)
print("STATUS: SUCCESS")
print("POS UI SEARCH PATCHED SAFELY")
print("=" * 80)
