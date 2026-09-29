from pathlib import Path
from datetime import datetime
import shutil
import ast
import re
import sys

ROOT = Path.cwd()
MAIN = ROOT / "app" / "ui" / "main_window.py"
BACKUPS = ROOT / "backups"

print("=" * 80)
print("REAL POS SEARCH FIX")
print("=" * 80)

if not MAIN.exists():
    raise SystemExit("ERROR: main_window.py غير موجود")

BACKUPS.mkdir(exist_ok=True)

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BACKUPS / f"before_real_pos_search_{stamp}.py"
shutil.copy2(MAIN, backup)

print("BACKUP:", backup)

source = MAIN.read_text(encoding="utf-8")

# ---------------------------------------------------------
# تحليل الملف
# ---------------------------------------------------------
tree = ast.parse(source)
print("ORIGINAL SYNTAX: OK")

# ---------------------------------------------------------
# العثور على class POS
# ---------------------------------------------------------
pos_class = None

for node in tree.body:
    if isinstance(node, ast.ClassDef) and node.name == "POS":
        pos_class = node
        break

if pos_class is None:
    shutil.copy2(backup, MAIN)
    raise SystemExit("ERROR: class POS غير موجود")

print("POS CLASS: FOUND")

# ---------------------------------------------------------
# العثور على search_product
# ---------------------------------------------------------
search_method = None

for node in pos_class.body:
    if isinstance(node, ast.FunctionDef) and node.name == "search_product":
        search_method = node
        break

if search_method is None:
    shutil.copy2(backup, MAIN)
    raise SystemExit("ERROR: POS.search_product غير موجود")

print("POS SEARCH METHOD: FOUND")

# ---------------------------------------------------------
# نقرأ النص الأصلي للدالة
# ---------------------------------------------------------
lines = source.splitlines(True)

start = search_method.lineno - 1
end = search_method.end_lineno

old_method = "".join(lines[start:end])

print("-" * 80)
print("OLD POS SEARCH METHOD:")
print(old_method[:2500])

# ---------------------------------------------------------
# نتحقق من وجود cart و result
# ---------------------------------------------------------
if "self.cart" not in source:
    shutil.copy2(backup, MAIN)
    raise SystemExit("ERROR: self.cart غير موجود")

if "self.result" not in source:
    shutil.copy2(backup, MAIN)
    raise SystemExit("ERROR: self.result غير موجود")

# ---------------------------------------------------------
# الدالة الجديدة
#
# نحافظ على نفس cart المتوقع من بقية POS:
# product_id / name / quantity / unit_price
# ---------------------------------------------------------
new_method = '''    def search_product(self):
        text = self.search.text().strip()

        if not text:
            self.result.setText("اكتب اسم المنتج أو SKU أو الباركود")
            return

        try:
            from app.services.pos_search_service import POSProductSearch

            searcher = POSProductSearch()
            results = searcher.search(text)

            if not results:
                self.result.setText("لم يتم العثور على المنتج")
                return

            product = results[0]

            pid = int(product["id"])
            name = str(product.get("name_ar") or product.get("name_en") or "")
            price = float(product.get("sale_price") or 0)

            # إضافة المنتج إلى السلة أو زيادة الكمية
            found = False

            for item in self.cart:
                if int(item["product_id"]) == pid:
                    item["quantity"] += 1
                    item["total"] = item["quantity"] * item["unit_price"]
                    found = True
                    break

            if not found:
                self.cart.append({
                    "product_id": pid,
                    "name": name,
                    "quantity": 1,
                    "unit_price": price,
                    "total": price
                })

            self.result.setText(
                f"تمت إضافة: {name} — السعر: {price:.2f}"
            )

            self.search.clear()
            self.reload_cart()

        except Exception as e:
            self.result.setText("خطأ في البحث")
            print("POS SEARCH ERROR:", e)
'''

# ---------------------------------------------------------
# التحقق من وجود reload_cart
# ---------------------------------------------------------
has_reload_cart = "def reload_cart(" in old_method or "def reload_cart(" in source

if not has_reload_cart:
    # لا نفترض وجود دالة غير موجودة.
    new_method = new_method.replace(
        "            self.reload_cart()\n",
        "            self.refresh_cart()\n"
    )

    if "def refresh_cart(" not in source:
        new_method = new_method.replace(
            "            self.refresh_cart()\n",
            ""
        )

# ---------------------------------------------------------
# استبدال الدالة فقط
# ---------------------------------------------------------
new_lines = lines[:start] + [new_method + "\n"] + lines[end:]

patched = "".join(new_lines)

# ---------------------------------------------------------
# فحص الصياغة
# ---------------------------------------------------------
try:
    ast.parse(patched)
    print("PATCHED SYNTAX: OK")
except Exception as e:
    shutil.copy2(backup, MAIN)
    raise SystemExit(
        f"PATCH FAILED - ORIGINAL RESTORED: {e}"
    )

# ---------------------------------------------------------
# حفظ
# ---------------------------------------------------------
MAIN.write_text(patched, encoding="utf-8")

# ---------------------------------------------------------
# اختبار نهائي
# ---------------------------------------------------------
try:
    final_source = MAIN.read_text(encoding="utf-8")
    final_tree = ast.parse(final_source)

    pos_found = False
    search_found = False

    for node in final_tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "POS":
            pos_found = True

            for method in node.body:
                if (
                    isinstance(method, ast.FunctionDef)
                    and method.name == "search_product"
                ):
                    search_found = True

    if not pos_found:
        raise RuntimeError("class POS اختفت")

    if not search_found:
        raise RuntimeError("search_product اختفت")

    if "POSProductSearch" not in final_source:
        raise RuntimeError("خدمة POSProductSearch غير مربوطة")

    print("FINAL SYNTAX: OK")
    print("POS CLASS: OK")
    print("SEARCH PRODUCT: OK")
    print("SEARCH SERVICE: CONNECTED")

except Exception as e:
    shutil.copy2(backup, MAIN)
    raise SystemExit(
        f"FINAL CHECK FAILED - RESTORED BACKUP: {e}"
    )

# ---------------------------------------------------------
# اختبار خدمة البحث مستقلة
# ---------------------------------------------------------
sys.path.insert(0, str(ROOT))

try:
    from app.services.pos_search_service import POSProductSearch

    s = POSProductSearch()

    for q in ["1", "PEN-001", "قلم", "دفتر", "628000000001"]:
        r = s.search(q)
        print(f"TEST {q}: {len(r)} result(s)")

    print("SEARCH SERVICE TEST: OK")

except Exception as e:
    shutil.copy2(backup, MAIN)
    raise SystemExit(
        f"SEARCH SERVICE TEST FAILED - RESTORED: {e}"
    )

print("=" * 80)
print("STATUS: SUCCESS")
print("REAL POS SEARCH IS NOW CONNECTED")
print("=" * 80)
