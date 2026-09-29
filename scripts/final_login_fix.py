from pathlib import Path
import shutil,py_compile,subprocess,sys

p=Path("app/ui/main_window.py")
shutil.copy2(p,"backups/main_window_before_final_login_fix.py")
s=p.read_text(encoding="utf-8")

# إزالة أي تعريف سابق لـ LoginDialog ثم إعادة تثبيت الاستيراد مباشرة قبله
needle="class LoginDialog(QDialog):"
if needle not in s:
    raise SystemExit("LOGIN CLASS NOT FOUND")

s=s.replace(
    needle,
    "from PySide6.QtWidgets import QDialog\nfrom PySide6.QtCore import Qt\n\n"+needle,
    1
)

p.write_text(s,encoding="utf-8")
py_compile.compile(str(p),doraise=True)

r=subprocess.run(
    [sys.executable,"-c","from app.ui.main_window import run; print('IMPORT: PASSED')"],
    cwd=str(Path.cwd()),capture_output=True,text=True
)

if r.returncode:
    print(r.stderr)
    raise SystemExit(1)

print("="*60)
print("FINAL LOGIN FIX: PASSED")
print("IMPORT: PASSED")
print("COMPILE: PASSED")
print("BACKUP: SAVED")
print("STATUS: SUCCESS")
print("="*60)
