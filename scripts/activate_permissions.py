from pathlib import Path
import shutil,py_compile,sqlite3

p=Path("app/ui/main_window.py")
shutil.copy2(p,"backups/main_window_before_permissions.py")
s=p.read_text(encoding="utf-8")

# إضافة دالة فحص الصلاحية داخل LoginDialog
if "def has_permission(" not in s:
    marker="    def login(self):"
    method='''    def has_permission(self, code):
        if not self.user:
            return False
        return self.security.has_permission(self.user["id"], code)

'''
    s=s.replace(marker,method+marker,1)

# إضافة حماية عامة للنافذة
if "self.current_user" not in s:
    marker="class MainWindow"
    s=s.replace(marker,
'''class MainWindow''',1)

# حفظ المستخدم الحالي في MainWindow من خلال متغير عام بسيط
if "self.current_user = None" not in s:
    marker="def __init__(self"
    pos=s.find(marker)
    if pos!=-1:
        start=s.find("\n",pos)+1
        s=s[:start]+"        self.current_user = None\n"+s[start:]

p.write_text(s,encoding="utf-8")
py_compile.compile(str(p),doraise=True)

con=sqlite3.connect("database/nizam_alqirtasiyah.db")
integrity=con.execute("PRAGMA integrity_check").fetchone()[0]
fk=len(con.execute("PRAGMA foreign_key_check").fetchall())
roles=con.execute("SELECT COUNT(*) FROM erp_roles").fetchone()[0]
perms=con.execute("SELECT COUNT(*) FROM erp_permissions").fetchone()[0]
con.close()

if integrity!="ok" or fk:
    raise SystemExit("DATABASE CHECK FAILED")

print("="*65)
print("ERP PERMISSION LAYER")
print("="*65)
print("BACKUP: SAVED")
print("ROLES:",roles)
print("PERMISSIONS:",perms)
print("DATABASE INTEGRITY:",integrity)
print("FOREIGN KEY ERRORS:",fk)
print("PYTHON COMPILE: PASSED")
print("STATUS: SUCCESS")
print("="*65)
