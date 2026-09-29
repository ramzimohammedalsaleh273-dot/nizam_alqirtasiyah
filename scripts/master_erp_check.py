from pathlib import Path
import shutil, sqlite3, py_compile, sys

print("="*72)
print("NIZAM ALQIRTASIYAH — MASTER ERP CHECK")
print("="*72)

# 1) Backup
p=Path("app/ui/main_window.py")
Path("backups").mkdir(exist_ok=True)
backup=Path("backups/main_window_master_check.py")
shutil.copy2(p,backup)

# 2) إصلاح الخطأ المحتمل في رسالة POS
s=p.read_text(encoding="utf-8")
s=s.replace("f\"المدفوع: {result.get('paid',0):.2f)}\"", "f\"المدفوع: {result.get('paid',0):.2f}\"")
p.write_text(s,encoding="utf-8")

# 3) Compile
for f in [
    "main.py",
    "app/ui/main_window.py",
    "app/services/erp_engine.py"
]:
    py_compile.compile(f,doraise=True)
print("PYTHON COMPILE: PASSED")

# 4) Database integrity
db=Path("database/nizam_alqirtasiyah.db")
con=sqlite3.connect(db)
cur=con.cursor()
integrity=cur.execute("PRAGMA integrity_check").fetchone()[0]
fk=cur.execute("PRAGMA foreign_key_check").fetchall()
print("DATABASE INTEGRITY:",integrity)
print("FOREIGN KEY ERRORS:",len(fk))

if integrity!="ok" or fk:
    raise RuntimeError("Database integrity failed")

# 5) Required tables
required=[
    "products","customers","suppliers",
    "sales","sale_items","sale_payments",
    "purchase_orders","purchase_order_items",
    "purchase_invoices","purchase_invoice_items",
    "stock_movements","cash_transactions",
    "journal_entries","journal_entry_lines",
    "accounts","tax_rates"
]
tables={r[0] for r in cur.execute(
    "SELECT name FROM sqlite_master WHERE type='table'"
).fetchall()}
missing=[x for x in required if x not in tables]

if missing:
    raise RuntimeError("Missing tables: "+", ".join(missing))

print("ERP TABLES:",len(required),"/",len(required))

# 6) Balance audit
debit=cur.execute(
    "SELECT COALESCE(SUM(debit),0) FROM journal_entry_lines"
).fetchone()[0]
credit=cur.execute(
    "SELECT COALESCE(SUM(credit),0) FROM journal_entry_lines"
).fetchone()[0]

print(f"ACCOUNTING DEBIT : {debit:.2f}")
print(f"ACCOUNTING CREDIT: {credit:.2f}")

if abs(debit-credit)>0.01:
    raise RuntimeError("Accounting is not balanced")

# 7) Operational counts
checks={}
for t in [
    "products","customers","suppliers","sales",
    "purchase_orders","purchase_invoices",
    "stock_movements","cash_transactions",
    "journal_entries"
]:
    checks[t]=cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]

for k,v in checks.items():
    print(f"{k:22} {v}")

con.close()

# 8) State update
state=Path(".lulu_state/build_state.json")
if state.exists():
    import json
    data=json.loads(state.read_text(encoding="utf-8"))
    data["erp_master_check"]="PASSED"
    data["erp_database_integrity"]="PASSED"
    data["erp_accounting_balance"]="PASSED"
    state.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")

print("-"*72)
print("MASTER ERP CHECK: PASSED")
print("DATABASE: PASSED")
print("ACCOUNTING: BALANCED")
print("POS CODE: COMPILED")
print("BACKUP: SAVED")
print("STATUS: SUCCESS")
print("="*72)
