from pathlib import Path
import shutil, py_compile, sys

p=Path("app/ui/main_window.py")
shutil.copy2(p,"backups/main_window_before_qdialog_guaranteed_fix.py")

s=p.read_text(encoding="utf-8")

# استيراد مستقل مضمون مهما كان شكل استيرادات PySide6 الموجودة
if "from PySide6.QtWidgets import QDialog" not in s:
    s="from PySide6.QtWidgets import QDialog\n"+s

if "from PySide6.QtCore import Qt" not in s:
    s="from PySide6.QtCore import Qt\n"+s

p.write_text(s,encoding="utf-8")

# 1) فحص ترجمة الملف
py_compile.compile(str(p),doraise=True)

# 2) فحص استيراد الملف فعلياً — قبل تشغيل البرنامج
import subprocess

test=subprocess.run(
    [sys.executable,"-c",
     "from app.ui.main_window import run, LoginDialog; print('MODULE IMPORT: PASSED')"],
    cwd=str(Path.cwd()),
    capture_output=True,
    text=True
)

print("="*72)
print("GUARANTEED LOGIN IMPORT REPAIR")
print("="*72)
print("BACKUP: SAVED")
print("QDialog: IMPORTED")
print("Qt: IMPORTED")
print("PYTHON COMPILE: PASSED")

if test.returncode != 0:
    print("MODULE IMPORT: FAILED")
    print(test.stdout)
    print(test.stderr)
    raise SystemExit(1)

print("MODULE IMPORT: PASSED")
print("STATUS: SUCCESS")
print("="*72)
