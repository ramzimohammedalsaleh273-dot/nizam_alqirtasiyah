from pathlib import Path
import shutil, py_compile, re

p=Path("app/ui/main_window.py")
shutil.copy2(p,"backups/main_window_before_qdialog_fix.py")
s=p.read_text(encoding="utf-8")

# إضافة QDialog و Qt إذا كانا ناقصين
if "QDialog" not in s.split("class LoginDialog",1)[0]:
    m=re.search(r"from PySide6\.QtWidgets import ([^\n]+)",s)
    if m:
        line=m.group(0)
        if "QDialog" not in line:
            line=line.rstrip()+", QDialog"
            s=s.replace(m.group(0),line,1)

# التأكد من QtCore
if "from PySide6.QtCore import" not in s:
    s="from PySide6.QtCore import Qt\n"+s
elif "from PySide6.QtCore import Qt" not in s:
    s=s.replace("from PySide6.QtCore import","from PySide6.QtCore import Qt,",1)

p.write_text(s,encoding="utf-8")

py_compile.compile(str(p),doraise=True)

print("="*72)
print("QDialog FIX")
print("="*72)
print("BACKUP: SAVED")
print("QDialog IMPORT: READY")
print("Qt IMPORT: READY")
print("PYTHON COMPILE: PASSED")
print("STATUS: SUCCESS")
print("="*72)
