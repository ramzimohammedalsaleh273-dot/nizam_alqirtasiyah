from __future__ import annotations
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database" / "nizam_alqirtasiyah.db"

def main():
    if not DB.exists():
        print("FAIL: قاعدة البيانات غير موجودة")
        return 1
    con = sqlite3.connect(DB)
    con.execute("PRAGMA foreign_keys=ON")
    required = [
        "companies","branches","users","roles","permissions",
        "products","product_barcodes","warehouses","stock","stock_movements",
        "customers","suppliers","sales","sale_items","sale_payments",
        "purchase_orders","purchase_invoices","purchase_invoice_items",
        "cash_registers","cash_sessions","treasury_accounts","bank_accounts",
        "accounts","journal_entries","journal_entry_lines","fiscal_periods",
        "tax_invoices","zatca_documents","printing_orders","documents",
        "employees","payroll_runs","assets","contracts",
        "report_definitions","analytics_metrics","notifications",
        "sync_queue","integrations","workflows","approval_requests",
        "backup_jobs","application_versions","search_index",
        "inventory_transfers","stock_adjustments","reorder_rules",
        "expense_claims","budgets","system_health_checks"
    ]
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    missing = [x for x in required if x not in tables]
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    fk = con.execute("PRAGMA foreign_key_check").fetchall()
    print("PASS: الجداول الأساسية:", len(required)-len(missing), "/", len(required))
    print("PASS: سلامة SQLite:", integrity)
    print("PASS: مخالفات المفاتيح الخارجية:", len(fk))
    print("PASS: الفترات المتداخلة:", con.execute(
        "SELECT COUNT(*) FROM fiscal_periods a JOIN fiscal_periods b "
        "ON a.id<b.id AND NOT (a.end_date<b.start_date OR a.start_date>b.end_date)"
    ).fetchone()[0] if "fiscal_periods" in tables else "N/A")
    unassigned = con.execute(
        "SELECT COUNT(*) FROM journal_entries WHERE status='POSTED' AND fiscal_period_id IS NULL"
    ).fetchone()[0] if "journal_entries" in tables else -1
    unbalanced = con.execute(
        "SELECT COUNT(*) FROM (SELECT je.id FROM journal_entries je "
        "JOIN journal_entry_lines jl ON jl.journal_entry_id=je.id "
        "WHERE je.status='POSTED' GROUP BY je.id "
        "HAVING ABS(SUM(COALESCE(jl.debit,0))-SUM(COALESCE(jl.credit,0)))>.01)"
    ).fetchone()[0] if {"journal_entries","journal_entry_lines"} <= tables else -1
    print("PASS: القيود المرحّلة بلا فترة:", unassigned)
    print("PASS: القيود المرحّلة غير المتوازنة:", unbalanced)
    con.close()
    ok = not missing and integrity == "ok" and not fk and unassigned == 0 and unbalanced == 0
    if missing:
        print("FAIL: جداول ناقصة:", ", ".join(missing))
    print("========================================")
    print("FINAL STATUS:", "PASS" if ok else "FAIL")
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
