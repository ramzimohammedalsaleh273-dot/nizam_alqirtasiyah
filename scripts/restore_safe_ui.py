from pathlib import Path
import shutil,datetime,py_compile

ROOT=Path.cwd()
UI=ROOT/"app/ui/main_window.py"
BACK=ROOT/"backups"

# البحث عن آخر نسخة احتياطية معروفة للواجهة
candidates=[]

for pattern in [
    "before_purchases_stage_*.py",
    "before_products_stage_*.py",
    "*main_window*.py"
]:
    candidates.extend(BACK.glob(pattern))

candidates=sorted(
    set(candidates),
    key=lambda x:x.stat().st_mtime,
    reverse=True
)

if not candidates:
    print("STATUS: FAILED")
    print("ERROR: لا توجد نسخة احتياطية للواجهة")
    raise SystemExit(1)

# اختيار نسخة قبل مرحلة المشتريات
source=None
for x in candidates:
    if "before_purchases_stage_" in x.name:
        source=x
        break

if source is None:
    source=candidates[0]

shutil.copy2(source,UI)

# التأكد من وجود MainWindow و run
s=UI.read_text(encoding="utf-8")

if "class MainWindow(" not in s:
    print("STATUS: FAILED")
    print("ERROR: النسخة الاحتياطية المختارة لا تحتوي MainWindow")
    raise SystemExit(1)

# حذف run القديمة وإعادة وضعها في النهاية
pos=s.find("\ndef run():")
if pos>=0:
    s=s[:pos]

s += '''

def run():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    window = MainWindow()
    window.show()

    return app.exec()
'''

UI.write_text(s,encoding="utf-8")

py_compile.compile(str(UI),doraise=True)
py_compile.compile("main.py",doraise=True)

print("="*80)
print("UI RESTORE")
print("="*80)
print("RESTORED FROM:",source)
print("MAINWINDOW: OK")
print("RUN: OK")
print("UI COMPILE: OK")
print("MAIN COMPILE: OK")
print("DATABASE UNTOUCHED: OK")
print("STATUS: SUCCESS")
print("="*80)
