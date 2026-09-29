from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys
import os
import re
import json

ROOT = Path.cwd()
APP = ROOT / "app"
UI = APP / "ui"
MAIN = UI / "main_window.py"
POS = UI / "pos_window.py"

BACKUPS = ROOT / "backups"
REPORTS = ROOT / "reports"

BACKUPS.mkdir(exist_ok=True)
REPORTS.mkdir(exist_ok=True)

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
report = REPORTS / f"stage_02_ui_runtime_{stamp}.txt"

lines = []

def log(x=""):
    print(x)
    lines.append(str(x))

def run_cmd(args, cwd=ROOT, timeout=30, env=None):
    try:
        p = subprocess.run(
            args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env
        )
        return p.returncode, p.stdout, p.stderr
    except Exception as e:
        return -999, "", repr(e)

log("=" * 80)
log("STAGE 02 - UI FOUNDATION + RUNTIME DIAGNOSTIC")
log("=" * 80)
log(f"ROOT: {ROOT}")
log(f"PYTHON: {sys.executable}")
log(f"PYTHON VERSION: {sys.version}")

# ============================================================
# 1. REQUIRED FILES
# ============================================================
log("")
log("[1] REQUIRED FILES")

required = [
    MAIN,
    POS,
    APP / "services" / "inventory_service.py",
    APP / "services" / "erp_engine.py",
    APP / "services" / "pos_service.py",
    APP / "database" / "connection.py",
]

missing = []

for p in required:
    if p.exists():
        log(f"OK: {p.relative_to(ROOT)}")
    else:
        log(f"MISSING: {p.relative_to(ROOT)}")
        missing.append(str(p.relative_to(ROOT)))

if missing:
    log("RESULT: REQUIRED FILES MISSING")
    report.write_text("\n".join(lines), encoding="utf-8")
    raise SystemExit(1)

# ============================================================
# 2. BACKUP CURRENT UI FILES
# ============================================================
log("")
log("[2] BACKUPS")

for p in [MAIN, POS]:
    backup = BACKUPS / f"stage_02_before_{p.stem}_{stamp}.py"
    shutil.copy2(p, backup)
    log(f"BACKUP: {backup}")

# ============================================================
# 3. MAIN WINDOW SOURCE ANALYSIS
# ============================================================
log("")
log("[3] MAIN WINDOW ANALYSIS")

main_text = MAIN.read_text(encoding="utf-8-sig")

checks = {
    "QApplication": "QApplication" in main_text,
    "QMainWindow": "QMainWindow" in main_text,
    "MainWindow class": "class MainWindow" in main_text,
    "run function": "def run(" in main_text,
    "main guard": 'if __name__ == "__main__":' in main_text,
    "window.show": ".show()" in main_text,
    "app.exec": "app.exec" in main_text,
    "Arabic": bool(re.search(r"[\u0600-\u06FF]", main_text)),
}

for name, value in checks.items():
    log(f"{name}: {value}")

# ============================================================
# 4. DETECT MOJIBAKE WITHOUT AUTOMATICALLY MODIFYING IT
# ============================================================
log("")
log("[4] ENCODING / MOJIBAKE CHECK")

mojibake_markers = [
    "ط§",
    "ط§ظ",
    "ظ„",
    "ظ†",
    "ظ…",
    "ظ„ط",
    "Ã",
    "Â",
    "â€",
    "ðŸ",
]

hits = []

for marker in mojibake_markers:
    count = main_text.count(marker)
    if count:
        hits.append((marker, count))

if hits:
    log("POSSIBLE MOJIBAKE FOUND:")
    for marker, count in hits:
        log(f"  {marker!r}: {count}")
else:
    log("NO COMMON MOJIBAKE MARKERS FOUND")

log("IMPORTANT: NO AUTOMATIC GLOBAL ENCODING REWRITE WAS PERFORMED.")

# ============================================================
# 5. PYTHON COMPILATION
# ============================================================
log("")
log("[5] PYTHON COMPILE")

py_files = [
    MAIN,
    POS,
    APP / "services" / "inventory_service.py",
    APP / "services" / "erp_engine.py",
    APP / "services" / "pos_service.py",
    APP / "database" / "connection.py",
]

compile_failed = False

for p in py_files:
    code, stdout, stderr = run_cmd(
        [sys.executable, "-m", "py_compile", str(p)]
    )

    if code == 0:
        log(f"COMPILE OK: {p.relative_to(ROOT)}")
    else:
        compile_failed = True
        log(f"COMPILE FAILED: {p.relative_to(ROOT)}")
        log(stderr)

# ============================================================
# 6. IMPORT TEST
# ============================================================
log("")
log("[6] IMPORT TEST")

env = os.environ.copy()
env["PYTHONPATH"] = str(ROOT)

imports = [
    "import app.ui.main_window; print('MAIN_WINDOW_IMPORT_OK')",
    "import app.ui.pos_window; print('POS_WINDOW_IMPORT_OK')",
    "from app.services.inventory_service import InventoryService; print('INVENTORY_SERVICE_IMPORT_OK')",
    "from app.services.erp_engine import ERP; print('ERP_ENGINE_IMPORT_OK')",
]

import_failed = False

for statement in imports:
    code, stdout, stderr = run_cmd(
        [sys.executable, "-c", statement],
        env=env
    )

    if stdout.strip():
        log(stdout.strip())

    if stderr.strip():
        log(stderr.strip())

    if code != 0:
        import_failed = True

# ============================================================
# 7. VERIFY MAIN GUARD
# ============================================================
log("")
log("[7] ENTRYPOINT CHECK")

if 'if __name__ == "__main__":' not in main_text:
    log("MAIN GUARD MISSING - ADDING SAFE GUARD")

    main_text = main_text.rstrip()
    main_text += '\n\nif __name__ == "__main__":\n    run()\n'

    MAIN.write_text(main_text, encoding="utf-8")
    log("MAIN GUARD ADDED")

else:
    log("MAIN GUARD PRESENT")

# Recompile after possible guard repair
code, stdout, stderr = run_cmd(
    [sys.executable, "-m", "py_compile", str(MAIN)]
)

log(f"POST-GUARD COMPILE EXIT: {code}")

if stderr.strip():
    log(stderr)

# ============================================================
# 8. VERIFY RUN FUNCTION STRUCTURE
# ============================================================
log("")
log("[8] RUN FUNCTION STRUCTURE")

current = MAIN.read_text(encoding="utf-8-sig")

run_match = re.search(
    r"(?ms)^def run\s*\(\s*\):.*?(?=^\S|\Z)",
    current
)

if run_match:
    log("RUN FUNCTION FOUND:")
    log(run_match.group(0))
else:
    log("RUN FUNCTION COULD NOT BE ISOLATED")

# ============================================================
# 9. DATABASE READ-ONLY HEALTH CHECK
# ============================================================
log("")
log("[9] DATABASE READ-ONLY HEALTH")

DB = ROOT / "database" / "nizam_alqirtasiyah.db"

if DB.exists():
    import sqlite3

    con = sqlite3.connect(DB)

    try:
        integrity = con.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        fk = con.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        log(f"DATABASE: {DB}")
        log(f"INTEGRITY: {integrity}")
        log(f"FOREIGN KEY ERRORS: {len(fk)}")

        tables = con.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type='table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """).fetchall()

        log(f"TABLE COUNT: {len(tables)}")

        important_tables = [
            "products",
            "product_barcodes",
            "customers",
            "suppliers",
            "sales",
            "sale_items",
            "purchase_orders",
            "purchase_invoices",
            "stock",
            "stock_balances",
            "stock_movements",
            "journal_entries",
            "journal_entry_lines",
            "workflow_steps",
            "payroll_periods",
            "payroll_runs",
            "bank_reconciliations",
            "asset_depreciation",
            "loyalty_transactions",
            "interbranch_transfers",
            "zatca_documents",
        ]

        log("")
        log("IMPORTANT TABLE COUNTS:")

        for table in important_tables:
            exists = con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (table,)
            ).fetchone()

            if exists:
                count = con.execute(
                    f'SELECT COUNT(*) FROM "{table}"'
                ).fetchone()[0]
                log(f"{table}: {count}")
            else:
                log(f"{table}: MISSING")

        # Accounting balance
        try:
            debit = con.execute(
                "SELECT COALESCE(SUM(debit),0) FROM journal_entry_lines"
            ).fetchone()[0]

            credit = con.execute(
                "SELECT COALESCE(SUM(credit),0) FROM journal_entry_lines"
            ).fetchone()[0]

            log("")
            log(f"ACCOUNTING DEBIT: {debit}")
            log(f"ACCOUNTING CREDIT: {credit}")
            log(f"ACCOUNTING DIFFERENCE: {float(debit or 0) - float(credit or 0)}")
        except Exception as e:
            log(f"ACCOUNTING CHECK ERROR: {e}")

    finally:
        con.close()
else:
    log("DATABASE MISSING")

# ============================================================
# 10. FINAL STATUS
# ============================================================
log("")
log("=" * 80)

if compile_failed or import_failed:
    status = "STAGE 02 DIAGNOSTIC FAILED - STOP"
else:
    status = "STAGE 02 DIAGNOSTIC SUCCESS"

log(status)
log("=" * 80)

report.write_text("\n".join(lines) + "\n", encoding="utf-8")

print("")
print("=" * 80)
print("STAGE 02 FINISHED")
print(f"REPORT: {report}")
print(f"STATUS: {status}")
print("=" * 80)
