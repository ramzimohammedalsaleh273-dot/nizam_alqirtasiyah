from pathlib import Path
import sqlite3,json
from datetime import datetime
R=Path(__file__).resolve().parents[1]; D=R/"database"/"nizam_alqirtasiyah.db"
c=sqlite3.connect(D)
c.executescript("""
CREATE TABLE IF NOT EXISTS notification_types(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 code TEXT UNIQUE NOT NULL,
 name TEXT NOT NULL,
 severity TEXT DEFAULT 'info',
 is_active INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS notifications(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 type_id INTEGER,
 title TEXT NOT NULL,
 message TEXT,
 user_id INTEGER,
 entity_type TEXT,
 entity_id INTEGER,
 is_read INTEGER DEFAULT 0,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP,
 read_at TEXT
);
CREATE TABLE IF NOT EXISTS notification_rules(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 code TEXT UNIQUE NOT NULL,
 name TEXT NOT NULL,
 condition_expression TEXT,
 is_active INTEGER DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id,is_read);
CREATE INDEX IF NOT EXISTS idx_notifications_created ON notifications(created_at);
""")
types=[
("LOW_STOCK","مخزون منخفض","warning"),
("CUSTOMER_DUE","مستحقات عميل","warning"),
("SUPPLIER_DUE","مستحقات مورد","warning"),
("CASH_DIFFERENCE","فرق الخزينة","critical"),
("CONTRACT_EXPIRY","انتهاء عقد","warning"),
("SYSTEM","تنبيه النظام","info")
]
for x in types:c.execute("INSERT OR IGNORE INTO notification_types(code,name,severity) VALUES(?,?,?)",x)
if c.execute("PRAGMA integrity_check").fetchone()[0]!="ok":raise RuntimeError("فشل integrity_check")
c.commit();c.close()
sf=R/".lulu_state"/"build_state.json";st=json.loads(sf.read_text(encoding="utf-8"))
if st.get("last_completed_stage",0)<20:raise RuntimeError("المرحلة 20 غير مكتملة")
st["last_completed_stage"]=21;st["last_completed_at"]=datetime.now().isoformat()
sf.write_text(json.dumps(st,ensure_ascii=False,indent=2),encoding="utf-8")
print("NOTIFICATIONS: OK")
print("ALERT TYPES: OK")
print("NOTIFICATION RULES: OK")
print("INTEGRITY: OK")
print("STATE: UPDATED")
print("STATUS: SUCCESS")
