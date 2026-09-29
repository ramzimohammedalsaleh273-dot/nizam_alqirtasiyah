from pathlib import Path
import sqlite3
import os
import json
from datetime import datetime
import bcrypt

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database" / "nizam_alqirtasiyah.db"

conn = sqlite3.connect(DB)
conn.execute("PRAGMA foreign_keys=ON")

conn.executescript("""
CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(500),
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(150) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    module VARCHAR(100) NOT NULL,
    action VARCHAR(100) NOT NULL,
    description VARCHAR(500)
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(100) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name VARCHAR(200) NOT NULL,
    phone VARCHAR(50),
    email VARCHAR(200),
    is_active INTEGER NOT NULL DEFAULT 1,
    is_locked INTEGER NOT NULL DEFAULT 0,
    failed_login_attempts INTEGER NOT NULL DEFAULT 0,
    last_login_at TEXT,
    password_changed_at TEXT,
    auto_lock_minutes INTEGER NOT NULL DEFAULT 15,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_roles (
    user_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    PRIMARY KEY(user_id,role_id),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(role_id) REFERENCES roles(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS role_permissions (
    role_id INTEGER NOT NULL,
    permission_id INTEGER NOT NULL,
    PRIMARY KEY(role_id,permission_id),
    FOREIGN KEY(role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY(permission_id) REFERENCES permissions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    session_token VARCHAR(255) NOT NULL UNIQUE,
    login_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_activity_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TEXT,
    logout_at TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS login_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(100) NOT NULL,
    success INTEGER NOT NULL DEFAULT 0,
    ip_address VARCHAR(100),
    attempted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reason VARCHAR(500)
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action VARCHAR(100) NOT NULL,
    module VARCHAR(100),
    entity_type VARCHAR(100),
    entity_id INTEGER,
    old_data TEXT,
    new_data TEXT,
    details TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_login_username ON login_attempts(username);
""")

roles = [
"المدير العام","مدير الفرع","المحاسب","مدير المخزون",
"مسؤول المشتريات","الكاشير","موظف الطباعة","الموارد البشرية","المراجع"
]

for r in roles:
    conn.execute("INSERT OR IGNORE INTO roles(name) VALUES (?)",(r,))

modules = [
("users","المستخدمون","manage"),
("roles","الأدوار","manage"),
("sales","المبيعات","manage"),
("purchases","المشتريات","manage"),
("inventory","المخزون","manage"),
("customers","العملاء","manage"),
("suppliers","الموردون","manage"),
("cash","الخزينة","manage"),
("banks","البنوك","manage"),
("accounting","المحاسبة","manage"),
("reports","التقارير","view"),
("printing","الطباعة","manage"),
("hr","الموارد البشرية","manage"),
("settings","الإعدادات","manage"),
("audit","سجل التدقيق","view")
]

for module,name,action in modules:
    code = f"{module}.{action}"
    conn.execute("""
    INSERT OR IGNORE INTO permissions(code,name,module,action)
    VALUES (?,?,?,?)
    """,(code,name,module,action))

admin = conn.execute(
    "SELECT id FROM users WHERE username='admin' LIMIT 1"
).fetchone()

if not admin:
    password = os.environ.get("LULU_INITIAL_ADMIN_PASSWORD")
    if not password:
        raise RuntimeError("يجب تعيين LULU_INITIAL_ADMIN_PASSWORD قبل إنشاء مستخدم admin")
    hashed = bcrypt.hashpw(password.encode(),bcrypt.gensalt()).decode()
    conn.execute("""
    INSERT INTO users
    (username,password_hash,full_name,password_changed_at)
    VALUES (?,?,?,?,)
    """.replace("(?,?,?,?,)","(?,?,?,?)"),
    ("admin",hashed,"مدير النظام",datetime.now().isoformat())
    )
    admin_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
else:
    admin_id = admin[0]

admin_role = conn.execute(
    "SELECT id FROM roles WHERE name='المدير العام'"
).fetchone()[0]

conn.execute(
    "INSERT OR IGNORE INTO user_roles(user_id,role_id) VALUES (?,?)",
    (admin_id,admin_role)
)

for row in conn.execute("SELECT id FROM permissions"):
    conn.execute(
        "INSERT OR IGNORE INTO role_permissions(role_id,permission_id) VALUES (?,?)",
        (admin_role,row[0])
    )

conn.commit()

required = [
"roles","permissions","users","user_roles",
"role_permissions","user_sessions","login_attempts","audit_logs"
]

existing = {
r[0] for r in conn.execute(
"SELECT name FROM sqlite_master WHERE type='table'"
).fetchall()
}

missing = [x for x in required if x not in existing]
if missing:
    raise RuntimeError("جداول ناقصة: "+",".join(missing))

if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
    raise RuntimeError("فشل integrity_check")

conn.close()

state_file = ROOT / ".lulu_state" / "build_state.json"
state = json.loads(state_file.read_text(encoding="utf-8"))
state["last_completed_stage"] = 2
state["last_completed_at"] = datetime.now().isoformat()
state_file.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding="utf-8")

print("SECURITY TABLES: OK")
print("ROLES: OK")
print("PERMISSIONS: OK")
print("ADMIN USER: OK")
print("INTEGRITY: OK")
print("STATE: UPDATED")
print("STATUS: SUCCESS")
print("اسم المستخدم الأول: admin")
print("كلمة المرور الأولية: يتم أخذها من LULU_INITIAL_ADMIN_PASSWORD إذا تم تعيينها.")
print("يجب تغييرها بعد الدخول.")



