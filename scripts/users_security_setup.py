from pathlib import Path
import sqlite3, shutil, hashlib, json
from datetime import datetime

print("="*72)
print("NIZAM ALQIRTASIYAH — USERS + ROLES + SECURITY")
print("="*72)

db=Path("database/nizam_alqirtasiyah.db")
Path("backups").mkdir(exist_ok=True)
backup=Path("backups/before_users_security.db")
shutil.copy2(db,backup)
print("BACKUP: PASSED")

con=sqlite3.connect(db)
cur=con.cursor()

def cols(t):
    return [x[1] for x in cur.execute(f"PRAGMA table_info({t})").fetchall()]

# صلاحيات
cur.execute("""
CREATE TABLE IF NOT EXISTS permissions (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 code VARCHAR(100) UNIQUE NOT NULL,
 name_ar VARCHAR(200) NOT NULL,
 module VARCHAR(100),
 is_active INTEGER DEFAULT 1
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS roles (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 code VARCHAR(100) UNIQUE NOT NULL,
 name_ar VARCHAR(200) NOT NULL,
 is_active INTEGER DEFAULT 1
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS role_permissions (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 role_id INTEGER NOT NULL,
 permission_id INTEGER NOT NULL,
 UNIQUE(role_id,permission_id),
 FOREIGN KEY(role_id) REFERENCES roles(id),
 FOREIGN KEY(permission_id) REFERENCES permissions(id)
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS user_roles (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 user_id INTEGER NOT NULL,
 role_id INTEGER NOT NULL,
 UNIQUE(user_id,role_id),
 FOREIGN KEY(user_id) REFERENCES users(id),
 FOREIGN KEY(role_id) REFERENCES roles(id)
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS login_sessions (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 user_id INTEGER,
 login_at DATETIME DEFAULT CURRENT_TIMESTAMP,
 logout_at DATETIME,
 status VARCHAR(30) DEFAULT 'ACTIVE'
)
""")

permissions=[
("POS.SALE","المبيعات","POS"),
("POS.RETURN","مرتجعات المبيعات","POS"),
("PURCHASE.CREATE","إنشاء المشتريات","PURCHASE"),
("PURCHASE.RECEIVE","استلام المشتريات","PURCHASE"),
("STOCK.ADJUST","تسوية المخزون","STOCK"),
("CUSTOMER.PAYMENT","تحصيل العملاء","CUSTOMERS"),
("SUPPLIER.PAYMENT","دفع الموردين","SUPPLIERS"),
("ACCOUNTING.POST","ترحيل القيود","ACCOUNTING"),
("REPORTS.VIEW","عرض التقارير","REPORTS"),
("USERS.MANAGE","إدارة المستخدمين","SECURITY"),
("SETTINGS.MANAGE","إدارة الإعدادات","SYSTEM"),
("BACKUP.MANAGE","النسخ الاحتياطي","SYSTEM"),
("AUDIT.VIEW","سجل التدقيق","SECURITY")
]

for x in permissions:
    cur.execute("""
    INSERT OR IGNORE INTO permissions
    (code,name_ar,module) VALUES (?,?,?)
    """,x)

roles=[
("ADMIN","مدير النظام"),
("MANAGER","مدير"),
("CASHIER","كاشير"),
("ACCOUNTANT","محاسب"),
("STOREKEEPER","أمين مخزن")
]

for x in roles:
    cur.execute("""
    INSERT OR IGNORE INTO roles
    (code,name_ar) VALUES (?,?)
    """,x)

admin_role=cur.execute(
"SELECT id FROM roles WHERE code='ADMIN'"
).fetchone()[0]

# المدير له كل الصلاحيات
for pid, in cur.execute(
"SELECT id FROM permissions WHERE is_active=1"
).fetchall():
    cur.execute("""
    INSERT OR IGNORE INTO role_permissions(role_id,permission_id)
    VALUES (?,?)
    """,(admin_role,pid))

# ربط المستخدم الموجود بمدير النظام
user=cur.execute("SELECT id FROM users ORDER BY id LIMIT 1").fetchone()
if user:
    cur.execute("""
    INSERT OR IGNORE INTO user_roles(user_id,role_id)
    VALUES (?,?)
    """,(user[0],admin_role))

# سجل أمني
cur.execute("""
INSERT INTO system_audit_log
(action,entity_type,description)
VALUES (?,?,?)
""",(
"SECURITY_SETUP",
"USERS",
"Users, roles and permissions initialized"
))

con.commit()

# تحقق
checks={
"permissions":cur.execute("SELECT COUNT(*) FROM permissions").fetchone()[0],
"roles":cur.execute("SELECT COUNT(*) FROM roles").fetchone()[0],
"role_permissions":cur.execute("SELECT COUNT(*) FROM role_permissions").fetchone()[0],
"user_roles":cur.execute("SELECT COUNT(*) FROM user_roles").fetchone()[0],
"login_sessions":cur.execute("SELECT COUNT(*) FROM login_sessions").fetchone()[0]
}

for k,v in checks.items():
    print(f"{k:20}: {v}")

integrity=cur.execute("PRAGMA integrity_check").fetchone()[0]
fk=cur.execute("PRAGMA foreign_key_check").fetchall()

print("DATABASE INTEGRITY:",integrity)
print("FOREIGN KEY ERRORS:",len(fk))

con.close()

if integrity!="ok" or fk:
    raise SystemExit("SECURITY DATABASE CHECK FAILED")

state=Path(".lulu_state/build_state.json")
if state.exists():
    try:
        data=json.loads(state.read_text(encoding="utf-8"))
    except:
        data={}
    data["users_roles_permissions"]="PASSED"
    data["security_layer"]="PASSED"
    state.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")

print("-"*72)
print("USERS          : READY")
print("ROLES          : READY")
print("PERMISSIONS    : READY")
print("LOGIN SESSIONS : READY")
print("AUDIT          : READY")
print("STATUS: SUCCESS")
print("="*72)
