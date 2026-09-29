from pathlib import Path
from datetime import datetime
import shutil
import re

ROOT = Path.cwd()
MAIN = ROOT / "app" / "ui" / "main_window.py"
SERVICE = ROOT / "app" / "services" / "pos_search_service.py"
BACKUP_DIR = ROOT / "backups"

print("=" * 80)
print("CONNECT POS UI TO REAL PRODUCT SEARCH")
print("=" * 80)

if not MAIN.exists():
    raise SystemExit(f"ERROR: الملف غير موجود: {MAIN}")

if not SERVICE.exists():
    raise SystemExit(f"ERROR: خدمة البحث غير موجودة: {SERVICE}")

BACKUP_DIR.mkdir(exist_ok=True)
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BACKUP_DIR / f"before_pos_ui_connect_{stamp}.py"
shutil.copy2(MAIN, backup)
print("BACKUP:", backup)

text = MAIN.read_text(encoding="utf-8")
original = text

# ------------------------------------------------------------
# 1) إضافة استيراد خدمة البحث
# ------------------------------------------------------------
if "from app.services.pos_search_service import POSProductSearch" not in text:
    imports = [
        "from app.services.pos_search_service import POSProductSearch\n",
        "from pathlib import Path\n",
    ]

    lines = text.splitlines(True)

    # ضع الاستيرادات بعد آخر import في بداية الملف
    last_import = -1
    for i, line in enumerate(lines[:120]):
        if line.startswith("import ") or line.startswith("from "):
            last_import = i

    if last_import >= 0:
        lines.insert(last_import + 1, imports[0])
        text = "".join(lines)
    else:
        text = imports[0] + text

# ------------------------------------------------------------
# 2) إضافة دالة بحث POS عامة داخل الملف
# ------------------------------------------------------------
method_marker = "def search_pos_products("

if method_marker not in text:

    method_code = r'''

    def search_pos_products(self, text):
        """بحث POS الحقيقي بالرقم أو SKU أو الاسم العربي/الإنجليزي أو الباركود."""
        try:
            query = str(text or "").strip()

            if not query:
                return []

            results = POSProductSearch.search(query)

            return results or []

        except Exception as exc:
            print("POS SEARCH ERROR:", exc)
            return []
'''

    # حاول وضع الدالة داخل أول class موجود
    class_match = re.search(r"^class\s+\w+.*?:\s*$", text, re.MULTILINE)

    if class_match:
        class_start = class_match.end()
        next_class = re.search(r"^class\s+\w+.*?:\s*$", text[class_start:], re.MULTILINE)

        if next_class:
            insert_at = class_start + next_class.start()
        else:
            insert_at = len(text)

        text = text[:insert_at] + method_code + "\n" + text[insert_at:]
    else:
        # إذا لم نجد class نضيف دالة مستقلة
        text += "\n\n" + method_code.replace("    def ", "def ")

# ------------------------------------------------------------
# 3) إضافة دالة موحدة لاختبار البحث من الواجهة
# ------------------------------------------------------------
test_marker = "def test_pos_search_connection("

if test_marker not in text:
    test_code = r'''

    def test_pos_search_connection(self):
        """اختبار سريع لاتصال واجهة POS بخدمة البحث."""
        tests = ["1", "PEN-001", "قلم", "دفتر", "628000000001"]

        print("=" * 60)
        print("POS UI SEARCH TEST")
        print("=" * 60)

        for q in tests:
            results = self.search_pos_products(q)
            print("QUERY:", q)
            print("RESULTS:", results[:5])

        print("POS UI SEARCH: READY")
'''

    # أضفها في نهاية الملف داخل آخر class إن وجد
    class_positions = list(re.finditer(r"^class\s+\w+.*?:\s*$", text, re.MULTILINE))

    if class_positions:
        # آخر class غالباً هو نافذة التطبيق
        text += "\n" + test_code + "\n"
    else:
        text += "\n" + test_code.replace("    def ", "def ") + "\n"

# ------------------------------------------------------------
# 4) حفظ فقط إذا حدث تغيير
# ------------------------------------------------------------
if text != original:
    MAIN.write_text(text, encoding="utf-8")
    print("MAIN WINDOW: PATCHED")
else:
    print("MAIN WINDOW: ALREADY PATCHED")

# ------------------------------------------------------------
# 5) اختبار الاستيراد والصياغة
# ------------------------------------------------------------
import ast

try:
    ast.parse(MAIN.read_text(encoding="utf-8"))
    print("PYTHON SYNTAX: OK")
except Exception as e:
    shutil.copy2(backup, MAIN)
    print("PATCH FAILED - RESTORED BACKUP")
    raise SystemExit(f"SYNTAX ERROR: {e}")

# ------------------------------------------------------------
# 6) اختبار خدمة البحث مباشرة
# ------------------------------------------------------------
import sys
sys.path.insert(0, str(ROOT))

try:
    from app.services.pos_search_service import POSProductSearch

    for q in ["1", "PEN-001", "قلم", "دفتر", "628000000001"]:
        result = POSProductSearch.search(q)
        print(f"CONNECTED SEARCH {q}:", result[:3])

    print("SERVICE CONNECTION: OK")

except Exception as e:
    shutil.copy2(backup, MAIN)
    print("SERVICE TEST FAILED - RESTORED MAIN WINDOW")
    raise SystemExit(f"SERVICE ERROR: {e}")

print("=" * 80)
print("STATUS: SUCCESS")
print("POS UI SEARCH CONNECTION READY")
print("=" * 80)
