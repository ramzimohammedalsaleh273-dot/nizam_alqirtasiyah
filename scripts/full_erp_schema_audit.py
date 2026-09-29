from pathlib import Path
import sqlite3
import json
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database" / "nizam_alqirtasiyah.db"
OUT = ROOT / "reports"
OUT.mkdir(exist_ok=True)

required = {
    "companies": ["id","name"],
    "branches": ["id","company_id","name"],
    "warehouses": ["id","branch_id","name"],
    "products": ["id","sku","name_ar","cost_price","sale_price"],
    "product_categories": ["id","name"],
    "customers": ["id"],
    "suppliers": ["id"],
    "sales": ["id"],
    "sale_items": ["id","sale_id","product_id"],
    "sale_payments": ["id","sale_id"],
    "purchase_orders": ["id"],
    "purchase_order_items": ["id","purchase_order_id","product_id"],
    "purchase_invoices": ["id"],
    "purchase_invoice_items": ["id","purchase_invoice_id","product_id"],
    "stock_balances": ["id","product_id","warehouse_id"],
    "stock_movements": ["id","product_id","warehouse_id"],
    "accounts": ["id","account_code","account_name"],
    "journal_entries": ["id"],
    "journal_entry_lines": ["id","journal_entry_id","account_id"],
    "cash_transactions": ["id"],
    "tax_rates": ["id","code","rate"],
    "tax_invoices": ["id"],
    "tax_transactions": ["id"],
    "audit_log": ["id"],
}

conn = sqlite3.connect(DB)
conn.execute("PRAGMA foreign_keys=ON")
tables = {r[0] for r in conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table'"
)}

report = {
    "generated_at": datetime.now().isoformat(),
    "database": str(DB),
    "tables": {},
    "missing_tables": [],
    "missing_columns": {},
    "relationships": {},
}

for table, cols in required.items():
    if table not in tables:
        report["missing_tables"].append(table)
        continue

    actual = [r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')]
    report["tables"][table] = actual
    missing = [c for c in cols if c not in actual]
    if missing:
        report["missing_columns"][table] = missing

links = [
    ("sales","sale_items","sales.id","sale_items.sale_id"),
    ("sales","sale_payments","sales.id","sale_payments.sale_id"),
    ("sale_items","products","sale_items.product_id","products.id"),
    ("purchase_orders","purchase_order_items","purchase_orders.id","purchase_order_items.purchase_order_id"),
    ("purchase_order_items","products","purchase_order_items.product_id","products.id"),
    ("purchase_invoices","purchase_invoice_items","purchase_invoices.id","purchase_invoice_items.purchase_invoice_id"),
    ("purchase_invoice_items","products","purchase_invoice_items.product_id","products.id"),
    ("stock_balances","products","stock_balances.product_id","products.id"),
    ("stock_movements","products","stock_movements.product_id","products.id"),
    ("stock_movements","warehouses","stock_movements.warehouse_id","warehouses.id"),
    ("journal_entry_lines","journal_entries","journal_entry_lines.journal_entry_id","journal_entries.id"),
    ("journal_entry_lines","accounts","journal_entry_lines.account_id","accounts.id"),
]

for a,b,x,y in links:
    report["relationships"][f"{a}->{b}"] = {
        "parent": x,
        "child": y,
        "parent_exists": a in tables,
        "child_exists": b in tables,
    }

counts = {}
for table in sorted(tables):
    try:
        counts[table] = conn.execute(
            f'SELECT COUNT(*) FROM "{table}"'
        ).fetchone()[0]
    except Exception:
        counts[table] = None

report["counts"] = counts

path = OUT / "full_erp_schema_audit.json"
path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

print("\nDATABASE: OK")
print("TABLES FOUND:", len(tables))
print("REQUIRED TABLES:", len(required))
print("MISSING TABLES:", len(report["missing_tables"]))
print("TABLES WITH MISSING COLUMNS:", len(report["missing_columns"]))
print("RELATIONSHIPS CHECKED:", len(links))
print("REPORT:", path)

print("\n--- CORE ERP COUNTS ---")
for t in [
    "products","customers","suppliers","sales","sale_items",
    "purchase_orders","purchase_order_items","purchase_invoices",
    "purchase_invoice_items","stock_balances","stock_movements",
    "accounts","journal_entries","journal_entry_lines"
]:
    print(f"{t}: {counts.get(t,'MISSING')}")

if report["missing_tables"]:
    print("\nMISSING TABLES:")
    for x in report["missing_tables"]:
        print(" -", x)

if report["missing_columns"]:
    print("\nMISSING COLUMNS:")
    for table, cols in report["missing_columns"].items():
        print(" -", table, ":", ", ".join(cols))

conn.close()
print("\nSTATUS: AUDIT COMPLETE")
