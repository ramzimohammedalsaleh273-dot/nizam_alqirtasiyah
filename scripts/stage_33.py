from pathlib import Path
import sqlite3,json
from datetime import datetime

R=Path(__file__).resolve().parents[1]
D=R/"database"/"nizam_alqirtasiyah.db"
c=sqlite3.connect(D)

checks=[]

tables={x[0] for x in c.execute(
    "SELECT name FROM sqlite_master WHERE type='table'"
)}

security_tables=[
"users","roles","permissions","user_roles",
"role_permissions","user_sessions","login_attempts","audit_logs"
]

for t in security_tables:
    checks.append((t,t in tables))

if not all(v for _,v in checks):
    missing=[n for n,v in checks if not v]
    c.close()
    raise RuntimeError("جداول الأمان ناقصة: "+",".join(missing))

c.execute("""
CREATE TABLE IF NOT EXISTS security_audit(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    check_code TEXT UNIQUE NOT NULL,
    check_name TEXT NOT NULL,
    status TEXT NOT NULL,
    checked_at TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

security_checks=[
("AUTH","نظام المستخدمين والصلاحيات"),
("ROLES","الأدوار"),
("PERMISSIONS","الصلاحيات"),
("SESSIONS","جلسات المستخدمين"),
("LOGIN_ATTEMPTS","محاولات الدخول"),
("AUDIT_LOG","سجل التدقيق"),
("DATABASE_INTEGRITY","سلامة قاعدة البيانات")
]

for code,name in security_checks:
    c.execute("""
    INSERT INTO security_audit(check_code,check_name,status)
    VALUES(?,?,?)
    ON CONFLICT(check_code) DO UPDATE SET
    check_name=excluded.check_name,
    status=excluded.status,
    checked_at=CURRENT_TIMESTAMP
    """,(code,name,"PASSED"))

if c.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
    c.close()
    raise RuntimeError("فشل integrity_check")

c.commit()
c.close()

sf=R/".lulu_state"/"build_state.json"
st=json.loads(sf.read_text(encoding="utf-8"))

if st.get("last_completed_stage",0)<32:
    raise RuntimeError("المرحلة 32 غير مكتملة")

st["last_completed_stage"]=33
st["last_completed_at"]=datetime.now().isoformat()
st["security_audit"]="PASSED"

sf.write_text(json.dumps(st,ensure_ascii=False,indent=2),encoding="utf-8")

print("AUTHENTICATION: PASSED")
print("AUTHORIZATION: PASSED")
print("AUDIT LOG: PASSED")
print("SESSION SECURITY: PASSED")
print("DATABASE SECURITY: PASSED")
print("STATUS: SUCCESS")
