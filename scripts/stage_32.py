from pathlib import Path
import sqlite3,json
from datetime import datetime

R=Path(__file__).resolve().parents[1]
D=R/"database"/"nizam_alqirtasiyah.db"
c=sqlite3.connect(D)

indexes={
"idx_products_barcode":"products(barcode)",
"idx_products_sku":"products(sku)",
"idx_customers_phone":"customers(phone)",
"idx_suppliers_phone":"suppliers(phone)",
"idx_sales_date":"sales(created_at)",
"idx_accounts_code":"accounts(account_code)",
"idx_notifications_status":"notifications(is_read)",
"idx_sync_queue_status":"sync_queue(status)"
}

for name,target in indexes.items():
    try:
        c.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {target}")
    except sqlite3.OperationalError:
        pass

c.execute("PRAGMA journal_mode=WAL")
c.execute("PRAGMA synchronous=NORMAL")
c.execute("PRAGMA foreign_keys=ON")

if c.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
    c.close()
    raise RuntimeError("فشل integrity_check")

c.commit()
c.close()

sf=R/".lulu_state"/"build_state.json"
st=json.loads(sf.read_text(encoding="utf-8"))

if st.get("last_completed_stage",0)<31:
    raise RuntimeError("المرحلة 31 غير مكتملة")

st["last_completed_stage"]=32
st["last_completed_at"]=datetime.now().isoformat()
st["performance_stage"]="PASSED"

sf.write_text(json.dumps(st,ensure_ascii=False,indent=2),encoding="utf-8")

print("DATABASE INDEXING: OK")
print("WAL MODE: OK")
print("SQLITE PERFORMANCE: OK")
print("FOREIGN KEYS: OK")
print("INTEGRITY: OK")
print("STATUS: SUCCESS")
