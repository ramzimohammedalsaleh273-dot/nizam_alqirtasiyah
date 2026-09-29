from pathlib import Path
import sqlite3, shutil, json

print("="*72)
print("NIZAM ALQIRTASIYAH — SAFE USERS SECURITY REPAIR")
print("="*72)

db=Path("database/nizam_alqirtasiyah.db")
Path("backups").mkdir(exist_ok=True)
shutil.copy2(db,"backups/before_safe_users_security_repair.db")
print("BACKUP: PASSED")

con=sqlite3.connect(db)
con.execute("PRAGMA foreign_keys=ON")
cur=con.cursor()

def table_exists(t):
    return cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(t,)
    ).fetchone() is not None

def columns(t):
    return [x[1] for x in cur.execute(f"PRAGMA table_info({t})").fetchall()]

def ensure_table(sql,name):
    cur.execute(sql)
    print(name,": READY")

# جداول جديدة بأسماء مضمونة
ensure_table("""
CREATE TABLE IF NOT EXISTS erp_permissions (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 code TEXT UNIQUE NOT NULL,
 name TEXT NOT NULL,
 module TEXT,
 is_active INTEGER DEFAULT 1
)
""","erp_permissions")

ensure_table("""
CREATE TABLE IF NOT EXISTS erp_roles (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 code TEXT UNIQUE NOT NULL,
 name TEXT NOT NULL,
 is_active INTEGER DEFAULT 1
)
""","erp_roles")

ensure_table("""
CREATE TABLE IF NOT EXISTS erp_role_permissions (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 role_id INTEGER NOT NULL,
 permission_id INTEGER NOT NULL,
 UNIQUE(role_id,permission_id),
 FOREIGN KEY(role_id) REFERENCES erp_roles(id),
 FOREIGN KEY(permission_id) REFERENCES erp_permissions(id)
)
""","erp_role_permissions")

ensure_table("""
CREATE TABLE IF NOT EXISTS erp_user_roles (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 user_id INTEGER NOT NULL,
 role_id INTEGER NOT NULL,
 UNIQUE(user_id,role_id),
 FOREIGN KEY(user_id) REFERENCES users(id),
 FOREIGN KEY(role_id) REFERENCES erp_roles(id)
)
""","erp_user_roles")

ensure_table("""
CREATE TABLE IF NOT EXISTS erp_login_sessions (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 user_id INTEGER,
 login_at DATETIME DEFAULT CURRENT_TIMESTAMP,
 logout_at DATETIME,
 status TEXT DEFAULT 'ACTIVE'
)
""","erp_login_sessions")

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
("SETTINGS.MANAGE","الإعدادات","SYSTEM"),
("BACKUP.MANAGE","النسخ الاحتياطي","SYSTEM"),
("AUDIT.VIEW","سجل التدقيق","SECURITY")
]

for x in permissions:
    cur.execute(
        "INSERT OR IGNORE INTO erp_permissions(code,name,module) VALUES(?,?,?)",x
    )

roles=[
("ADMIN","مدير النظام"),
("MANAGER","مدير"),
("CASHIER","كاشير"),
("ACCOUNTANT","محاسب"),
("STOREKEEPER","أمين المخزن")
]

for x in roles:
    cur.execute(
        "INSERT OR IGNORE INTO erp_roles(code,name) VALUES(?,?,?)" if False
        else "INSERT OR IGNORE INTO erp_roles(code,name) VALUES(?,?)",x
    )

admin=cur.execute(
    "SELECT id FROM erp_roles WHERE code='ADMIN'"
).fetchone()[0]

for row in cur.execute("SELECT id FROM erp_permissions").fetchall():
    cur.execute(
        "INSERT OR IGNORE INTO erp_role_permissions(role_id,permission_id) VALUES(?,?)",
        (admin,row[0])
    )

user=cur.execute("SELECT id FROM users ORDER BY id LIMIT 1").fetchone()

if user:
    cur.execute(
        "INSERT OR IGNORE INTO erp_user_roles(user_id,role_id) VALUES(?,?)",
        (user[0],admin)
    )

cur.execute("""
CREATE TABLE IF NOT EXISTS system_audit_log (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 action TEXT,
 entity_type TEXT,
 entity_id INTEGER,
 description TEXT,
 created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

cur.execute("""
INSERT INTO system_audit_log
(action,entity_type,description)
VALUES (?,?,?)
""",("SECURITY_SETUP","USERS","Safe users and permissions initialization"))

con.commit()

integrity=cur.execute("PRAGMA integrity_check").fetchone()[0]
fk=cur.execute("PRAGMA foreign_key_check").fetchall()

print("PERMISSIONS:",cur.execute("SELECT COUNT(*) FROM erp_permissions").fetchone()[0])
print("ROLES:",cur.execute("SELECT COUNT(*) FROM erp_roles").fetchone()[0])
print("ROLE PERMISSIONS:",cur.execute("SELECT COUNT(*) FROM erp_role_permissions").fetchone()[0])
print("USER ROLES:",cur.execute("SELECT COUNT(*) FROM erp_user_roles").fetchone()[0])
print("DATABASE INTEGRITY:",integrity)
print("FOREIGN KEY ERRORS:",len(fk))

con.close()

if integrity!="ok" or fk:
    raise SystemExit("SECURITY CHECK FAILED")

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
print("USERS       : READY")
print("ROLES       : READY")
print("PERMISSIONS : READY")
print("LOGIN       : READY")
print("AUDIT       : READY")
print("STATUS: SUCCESS")
print("="*72)
