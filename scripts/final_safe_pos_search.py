from pathlib import Path
from datetime import datetime
import shutil
import ast
import re
import inspect

ROOT = Path.cwd()
MAIN = ROOT / "app" / "ui" / "main_window.py"
SERVICE = ROOT / "app" / "services" / "pos_search_service.py"
BACKUPS = ROOT / "backups"

print("=" * 80)
print("FINAL SAFE POS SEARCH CONNECTION")
print("=" * 80)

if not MAIN.exists():
    raise SystemExit("ERROR: main_window.py غير موجود")

if not SERVICE.exists():
    raise SystemExit("ERROR: pos_search_service.py غير موجود")

BACKUPS.mkdir(exist_ok=True)
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

backup = BACKUPS / f"before_final_pos_search_{stamp}.py"
shutil.copy2(MAIN, backup)

print("BACKUP:", backup)

original = MAIN.read_text(encoding="utf-8")

# ---------------------------------------------------------
# فحص الملف الأصلي
# ---------------------------------------------------------
try:
    ast.parse(original)
    print("ORIGINAL SYNTAX: OK")
except Exception as e:
    raise SystemExit(f"ERROR: main_window.py غير سليم: {e}")

# ---------------------------------------------------------
# فحص خدمة البحث ومعرفة طريقة الاستدعاء الصحيحة
# ---------------------------------------------------------
import sys
sys.path.insert(0, str(ROOT))

try:
    from app.services.pos_search_service import POSProductSearch

    print("SEARCH CLASS:", POSProductSearch)

    search_signature = inspect.signature(POSProductSearch.search)
    print("SEARCH SIGNATURE:", search_signature)

    # إنشاء كائن الخدمة حسب constructor
    try:
        searcher = POSProductSearch()
        print("SERVICE INSTANCE: CREATED")
    except TypeError as e:
        print("DEFAULT CONSTRUCTOR FAILED:", e)

        try:
            searcher = POSProductSearch(
                str(ROOT / "database" / "nizam_alqirtasiyah.db")
            )
            print("SERVICE INSTANCE WITH DB PATH: CREATED")
        except Exception as e2:
            raise SystemExit(f"SERVICE INSTANCE ERROR: {e2}")

    # اختبار حقيقي
    tests = ["1", "PEN-001", "قلم", "دفتر", "628000000001"]

    print("-" * 80)
    print("REAL SERVICE TEST")

    for q in tests:
        result = searcher.search(q)
        print(f"SEARCH {q}: {result[:3]}")

    print("SERVICE TEST: OK")

except Exception as e:
    shutil.copy2(backup, MAIN)
    raise SystemExit(f"SERVICE TEST FAILED: {e}")

# ---------------------------------------------------------
# تجهيز main_window.py
# ---------------------------------------------------------
text = original

import_line = "from app.services.pos_search_service import POSProductSearch"

if import_line not in text:
    lines = text.splitlines(True)

    # بعد آخر import في أول 100 سطر
    last_import = -1

    for i, line in enumerate(lines[:120]):
        stripped = line.strip()

        if stripped.startswith("import ") or stripped.startswith("from "):
            last_import = i

    if last_import >= 0:
        lines.insert(last_import + 1, import_line + "\n")
    else:
        lines.insert(0, import_line + "\n")

    text = "".join(lines)

# ---------------------------------------------------------
# إزالة الدالة القديمة إن كانت موجودة
# ---------------------------------------------------------
pattern = re.compile(
    r"\n    def search_pos_products\(self, text\):.*?(?=\n    def |\nclass |\Z)",
    re.DOTALL
)

text = pattern.sub("", text)

# ---------------------------------------------------------
# إضافة الدالة الصحيحة
# ---------------------------------------------------------
classes = list(re.finditer(
    r"^class\s+[A-Za-z_]\w*(?:\([^)]*\))?\s*:\s*$",
    text,
    re.MULTILINE
))

if not classes:
    shutil.copy2(backup, MAIN)
    raise SystemExit("ERROR: لم يتم العثور على class في main_window.py")

class_match = classes[0]

method = '''
    def search_pos_products(self, text):
        """بحث POS الحقيقي بالرقم أو SKU أو الاسم أو الباركود."""
        try:
            query = str(text or "").strip()

            if not query:
                return []

            # خدمة البحث معرفة ككائن، لذلك ننشئ نسخة منها
            try:
                searcher = POSProductSearch()
            except TypeError:
                searcher = POSProductSearch(
                    str(Path.cwd() / "database" / "nizam_alqirtasiyah.db")
                )

            return searcher.search(query) or []

        except Exception as exc:
            print("POS SEARCH ERROR:", exc)
            return []
'''

text = text[:class_match.end()] + method + text[class_match.end():]

# ---------------------------------------------------------
# فحص syntax قبل الحفظ
# ---------------------------------------------------------
try:
    ast.parse(text)
    print("PATCHED SYNTAX: OK")
except Exception as e:
    shutil.copy2(backup, MAIN)
    raise SystemExit(f"PATCH SYNTAX FAILED: {e}")

MAIN.write_text(text, encoding="utf-8")

print("MAIN WINDOW: PATCHED")

# ---------------------------------------------------------
# إعادة فحص الملف بعد الحفظ
# ---------------------------------------------------------
try:
    ast.parse(MAIN.read_text(encoding="utf-8"))
    print("FINAL SYNTAX: OK")
except Exception as e:
    shutil.copy2(backup, MAIN)
    raise SystemExit(f"FINAL CHECK FAILED: {e}")

print("=" * 80)
print("STATUS: SUCCESS")
print("POS SEARCH SERVICE CONNECTED CORRECTLY")
print("=" * 80)
