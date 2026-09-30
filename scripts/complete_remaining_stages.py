from __future__ import annotations
import json
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database" / "nizam_alqirtasiyah.db"
BACKUPS = ROOT / "backups"
STATE = ROOT / ".lulu_state" / "build_state.json"
PYTHON = sys.executable

def backup():
    if not DB.exists():
        raise RuntimeError(f"قاعدة البيانات غير موجودة: {DB}")
    BACKUPS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = BACKUPS / f"before_remaining_stages_{stamp}.db"
    shutil.copy2(DB, target)
    return target

def run_stage(n: int):
    path = ROOT / "scripts" / f"stage_{n:02d}.py"
    if not path.exists():
        raise RuntimeError(f"ملف المرحلة غير موجود: {path}")
    print(f"\n========== المرحلة {n:02d} ==========")
    p = subprocess.run([PYTHON, str(path)], cwd=ROOT)
    if p.returncode != 0:
        raise RuntimeError(f"فشلت المرحلة {n:02d} برمز {p.returncode}")
    print(f"STAGE {n:02d}: SUCCESS")

def harden_schema():
    print("\n========== تقوية المخطط التشغيلي ==========")
    con = sqlite3.connect(DB)
    con.execute("PRAGMA foreign_keys=ON")
    con.executescript("""
    CREATE TABLE IF NOT EXISTS inventory_transfers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transfer_no TEXT UNIQUE NOT NULL,
        from_warehouse_id INTEGER NOT NULL,
        to_warehouse_id INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'draft',
        notes TEXT,
        created_by INTEGER,
        approved_by INTEGER,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        completed_at TEXT
    );
    CREATE TABLE IF NOT EXISTS inventory_transfer_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transfer_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity REAL NOT NULL,
        unit_cost REAL NOT NULL DEFAULT 0,
        FOREIGN KEY(transfer_id) REFERENCES inventory_transfers(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS stock_adjustments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        adjustment_no TEXT UNIQUE NOT NULL,
        warehouse_id INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'draft',
        reason TEXT,
        created_by INTEGER,
        approved_by INTEGER,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        posted_at TEXT
    );
    CREATE TABLE IF NOT EXISTS stock_adjustment_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        adjustment_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        counted_quantity REAL NOT NULL DEFAULT 0,
        system_quantity REAL NOT NULL DEFAULT 0,
        difference_quantity REAL NOT NULL DEFAULT 0,
        unit_cost REAL NOT NULL DEFAULT 0,
        FOREIGN KEY(adjustment_id) REFERENCES stock_adjustments(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS reorder_rules(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        warehouse_id INTEGER,
        min_quantity REAL NOT NULL DEFAULT 0,
        max_quantity REAL NOT NULL DEFAULT 0,
        reorder_quantity REAL NOT NULL DEFAULT 0,
        preferred_supplier_id INTEGER,
        is_active INTEGER NOT NULL DEFAULT 1,
        UNIQUE(product_id,warehouse_id)
    );
    CREATE TABLE IF NOT EXISTS expense_claims(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        claim_no TEXT UNIQUE NOT NULL,
        employee_id INTEGER,
        amount REAL NOT NULL DEFAULT 0,
        expense_date TEXT NOT NULL,
        category TEXT,
        status TEXT NOT NULL DEFAULT 'draft',
        description TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS budgets(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        fiscal_year INTEGER,
        status TEXT NOT NULL DEFAULT 'draft',
        total_amount REAL NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS budget_lines(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        budget_id INTEGER NOT NULL,
        account_code TEXT,
        cost_center_code TEXT,
        period TEXT,
        amount REAL NOT NULL DEFAULT 0,
        FOREIGN KEY(budget_id) REFERENCES budgets(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS system_health_checks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        check_code TEXT UNIQUE NOT NULL,
        check_name TEXT NOT NULL,
        status TEXT NOT NULL,
        details TEXT,
        checked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_inventory_transfer_items_transfer ON inventory_transfer_items(transfer_id);
    CREATE INDEX IF NOT EXISTS idx_stock_adjustment_items_adjustment ON stock_adjustment_items(adjustment_id);
    CREATE INDEX IF NOT EXISTS idx_reorder_rules_product ON reorder_rules(product_id);
    CREATE INDEX IF NOT EXISTS idx_expense_claims_date ON expense_claims(expense_date);
    CREATE INDEX IF NOT EXISTS idx_budget_lines_budget ON budget_lines(budget_id);
    """)
    con.commit()
    con.close()

def validate():
    print("\n========== التحقق النهائي ==========")
    con = sqlite3.connect(DB)
    con.execute("PRAGMA foreign_keys=ON")
    required = {
        "products","product_barcodes","warehouses","stock","stock_movements",
        "customers","suppliers","sales","sale_items","sale_payments",
        "purchase_orders","purchase_invoices","purchase_invoice_items",
        "loyalty_accounts","promotions","coupons","bank_accounts",
        "accounts","journal_entries","journal_entry_lines","fiscal_periods",
        "tax_invoices","zatca_documents","printing_orders","documents",
        "employees","payroll_runs","assets","contracts","report_definitions",
        "analytics_metrics","notifications","sync_queue","integrations",
        "workflows","approval_requests","backup_jobs","application_versions",
        "search_index","inventory_transfers","stock_adjustments","reorder_rules",
        "expense_claims","budgets","system_health_checks"
    }
    existing = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    missing = sorted(required - existing)
    if missing:
        con.close()
        raise RuntimeError("جداول ناقصة: " + ", ".join(missing))
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        con.close()
        raise RuntimeError("PRAGMA integrity_check فشل: " + str(integrity))
    fk = con.execute("PRAGMA foreign_key_check").fetchall()
    if fk:
        con.close()
        raise RuntimeError(f"قيود مفاتيح خارجية مخالفة: {len(fk)}")
    con.close()

def update_state():
    STATE.parent.mkdir(parents=True, exist_ok=True)
    state = {}
    if STATE.exists():
        state = json.loads(STATE.read_text(encoding="utf-8"))
    state["last_completed_stage"] = 34
    state["last_completed_at"] = datetime.now().isoformat()
    state["remaining_stages_completed"] = True
    state["offline_first"] = True
    state["enterprise_hardening"] = True
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

def main():
    print("نظام القرطاسية — تنفيذ الدفعات المتبقية 3 إلى 9")
    print("لن يتم حذف قاعدة البيانات أو إنشاء قاعدة بديلة.")
    backup_path = backup()
    print("BACKUP CREATED:", backup_path)
    try:
        for n in range(3, 29):
            run_stage(n)
        run_stage(29)
        for n in range(30, 35):
            run_stage(n)
        harden_schema()
        validate()
        update_state()
        print("\n========================================")
        print("ALL REMAINING STAGES: SUCCESS")
        print("STAGES 03-34: COMPLETED")
        print("DATABASE INTEGRITY: PASS")
        print("BACKUP:", backup_path)
        print("========================================")
    except Exception as exc:
        print("\n========================================")
        print("REMAINING STAGES: FAILED")
        print("ERROR:", exc)
        print("BACKUP:", backup_path)
        print("========================================")
        raise

if __name__ == "__main__":
    main()
