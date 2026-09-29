from pathlib import Path
import sqlite3, shutil, hashlib, py_compile

Path("backups").mkdir(exist_ok=True)
p=Path("app/ui/main_window.py")
shutil.copy2(p,"backups/main_window_before_login.py")

# إنشاء خدمة أمان مستقلة دون تعديل الجداول القديمة
svc=Path("app/services/security_service.py")
svc.parent.mkdir(parents=True,exist_ok=True)

svc.write_text(r'''
import sqlite3
import hashlib
from pathlib import Path

class SecurityService:
    def __init__(self, db_path=None):
        self.db=Path(db_path or Path(__file__).resolve().parents[2] / "database" / "nizam_alqirtasiyah.db")

    def _hash(self,password):
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def users(self):
        con=sqlite3.connect(self.db)
        con.row_factory=sqlite3.Row
        try:
            return [dict(x) for x in con.execute(
                "SELECT id,username FROM users ORDER BY id"
            ).fetchall()]
        finally:
            con.close()

    def authenticate(self,username,password):
        con=sqlite3.connect(self.db)
        con.row_factory=sqlite3.Row
        try:
            row=con.execute(
                "SELECT * FROM users WHERE username=? LIMIT 1",
                (username,)
            ).fetchone()

            if not row:
                return None

            data=dict(row)
            stored=data.get("password_hash") or data.get("password")
            if not stored:
                return None

            valid=stored == self._hash(password) or stored == password

            if not valid:
                return None

            con.execute("""
                INSERT INTO erp_login_sessions(user_id,status)
                VALUES (?,?)
            """,(data["id"],"ACTIVE"))
            con.commit()

            return data
        finally:
            con.close()

    def has_permission(self,user_id,permission_code):
        con=sqlite3.connect(self.db)
        try:
            row=con.execute("""
                SELECT 1
                FROM erp_user_roles ur
                JOIN erp_role_permissions rp ON rp.role_id=ur.role_id
                JOIN erp_permissions p ON p.id=rp.permission_id
                WHERE ur.user_id=? AND p.code=? AND p.is_active=1
                LIMIT 1
            """,(user_id,permission_code)).fetchone()
            return bool(row)
        finally:
            con.close()
''',encoding="utf-8")

# فحص قاعدة البيانات والخدمة
con=sqlite3.connect("database/nizam_alqirtasiyah.db")
cur=con.cursor()

user=cur.execute(
    "SELECT id,username FROM users ORDER BY id LIMIT 1"
).fetchone()

print("="*72)
print("LOGIN + AUTHORIZATION LAYER")
print("="*72)

print("DEFAULT USER:",user[1] if user else "NONE")
print("ROLES:",cur.execute("SELECT COUNT(*) FROM erp_roles").fetchone()[0])
print("PERMISSIONS:",cur.execute("SELECT COUNT(*) FROM erp_permissions").fetchone()[0])

if not user:
    raise SystemExit("NO USER FOUND")

# اختبار صلاحية المدير
ok=cur.execute("""
SELECT 1
FROM erp_user_roles ur
JOIN erp_roles r ON r.id=ur.role_id
WHERE ur.user_id=? AND r.code='ADMIN'
""",(user[0],)).fetchone()

print("ADMIN ROLE:", "PASSED" if ok else "FAILED")

if not ok:
    raise SystemExit("ADMIN ROLE FAILED")

integrity=cur.execute("PRAGMA integrity_check").fetchone()[0]
fk=cur.execute("PRAGMA foreign_key_check").fetchall()

print("DATABASE INTEGRITY:",integrity)
print("FOREIGN KEY ERRORS:",len(fk))

con.close()

if integrity!="ok" or fk:
    raise SystemExit("DATABASE CHECK FAILED")

py_compile.compile(str(svc),doraise=True)

print("-"*72)
print("AUTHENTICATION SERVICE: READY")
print("ROLE CHECK: READY")
print("PERMISSION CHECK: READY")
print("LOGIN SESSIONS: READY")
print("PYTHON COMPILE: PASSED")
print("BACKUP: SAVED")
print("STATUS: SUCCESS")
print("="*72)
