from pathlib import Path
import sqlite3
import shutil
import sys
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "database" / "nizam_alqirtasiyah.db"
REPORTS = ROOT / "reports"
BACKUPS = ROOT / "backups"

REPORTS.mkdir(parents=True, exist_ok=True)
BACKUPS.mkdir(parents=True, exist_ok=True)

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
report = REPORTS / f"comprehensive_repair_{stamp}.txt"

lines = []

def log(msg):
    print(msg)
    lines.append(str(msg))

def table_exists(con, name):
    return con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,)
    ).fetchone() is not None

def columns(con, table):
    if not table_exists(con, table):
        return []
    return [r[1] for r in con.execute(f'PRAGMA table_info("{table}")').fetchall()]

def ensure_table(con, sql, name):
    try:
        con.execute(sql)
        log(f"TABLE OK/CREATED: {name}")
    except Exception as e:
        log(f"TABLE SKIPPED: {name} -> {e}")

def ensure_column(con, table, column, definition):
    try:
        if not table_exists(con, table):
            log(f"COLUMN SKIPPED: {table}.{column} (table missing)")
            return
        if column not in columns(con, table):
            con.execute(
                f'ALTER TABLE "{table}" ADD COLUMN "{column}" {definition}'
            )
            log(f"COLUMN CREATED: {table}.{column}")
        else:
            log(f"COLUMN EXISTS: {table}.{column}")
    except Exception as e:
        log(f"COLUMN SKIPPED: {table}.{column} -> {e}")

if not DB.exists():
    log(f"FATAL: DATABASE NOT FOUND: {DB}")
    report.write_text("\n".join(lines), encoding="utf-8")
    sys.exit(1)

con = sqlite3.connect(DB)
con.execute("PRAGMA foreign_keys=ON")

log("=" * 70)
log("الإصلاح الشامل الآمن — نظام القرطاسية")
log("=" * 70)

# ------------------------------------------------------------
# 1. الجداول الأساسية للأجزاء التي ظهر أنها ناقصة
# ------------------------------------------------------------

ensure_table(con, """
CREATE TABLE IF NOT EXISTS workflow_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_id INTEGER,
    step_no INTEGER DEFAULT 1,
    step_name TEXT,
    role_id INTEGER,
    required_permission TEXT,
    is_required INTEGER DEFAULT 1,
    created_at TEXT
)
""", "workflow_steps")

ensure_table(con, """
CREATE TABLE IF NOT EXISTS payroll_periods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    period_code TEXT,
    start_date TEXT,
    end_date TEXT,
    status TEXT DEFAULT 'OPEN',
    created_at TEXT
)
""", "payroll_periods")

ensure_table(con, """
CREATE TABLE IF NOT EXISTS payroll_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    period_id INTEGER,
    run_number TEXT,
    status TEXT DEFAULT 'DRAFT',
    total_gross REAL DEFAULT 0,
    total_deductions REAL DEFAULT 0,
    total_net REAL DEFAULT 0,
    created_at TEXT
)
""", "payroll_runs")

ensure_table(con, """
CREATE TABLE IF NOT EXISTS bank_reconciliations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bank_account_id INTEGER,
    statement_date TEXT,
    statement_balance REAL DEFAULT 0,
    system_balance REAL DEFAULT 0,
    difference REAL DEFAULT 0,
    status TEXT DEFAULT 'DRAFT',
    notes TEXT,
    created_at TEXT
)
""", "bank_reconciliations")

ensure_table(con, """
CREATE TABLE IF NOT EXISTS loyalty_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    loyalty_account_id INTEGER,
    transaction_type TEXT,
    points REAL DEFAULT 0,
    reference_type TEXT,
    reference_id INTEGER,
    balance_after REAL DEFAULT 0,
    created_at TEXT
)
""", "loyalty_transactions")

ensure_table(con, """
CREATE TABLE IF NOT EXISTS asset_depreciation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER,
    period TEXT,
    amount REAL DEFAULT 0,
    book_value REAL DEFAULT 0,
    created_at TEXT
)
""", "asset_depreciation")

ensure_table(con, """
CREATE TABLE IF NOT EXISTS interbranch_transfers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transfer_number TEXT,
    from_branch_id INTEGER,
    to_branch_id INTEGER,
    status TEXT DEFAULT 'DRAFT',
    notes TEXT,
    created_at TEXT
)
""", "interbranch_transfers")

ensure_table(con, """
CREATE TABLE IF NOT EXISTS integration_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    integration_id INTEGER,
    level TEXT,
    message TEXT,
    payload TEXT,
    created_at TEXT
)
""", "integration_logs")

# ------------------------------------------------------------
# 2. أعمدة مساعدة غير مدمرة
# ------------------------------------------------------------

ensure_column(con, "products", "name_en", "TEXT")
ensure_column(con, "products", "description", "TEXT")
ensure_column(con, "products", "reorder_point", "REAL DEFAULT 0")
ensure_column(con, "products", "min_stock", "REAL DEFAULT 0")
ensure_column(con, "products", "max_stock", "REAL DEFAULT 0")

ensure_column(con, "customers", "credit_limit", "REAL DEFAULT 0")
ensure_column(con, "customers", "opening_balance", "REAL DEFAULT 0")
ensure_column(con, "customers", "current_balance", "REAL DEFAULT 0")

ensure_column(con, "sales", "paid_amount", "REAL DEFAULT 0")
ensure_column(con, "sales", "due_amount", "REAL DEFAULT 0")
ensure_column(con, "sales", "discount_amount", "REAL DEFAULT 0")

ensure_column(con, "purchase_invoices", "paid_amount", "REAL DEFAULT 0")
ensure_column(con, "purchase_invoices", "due_amount", "REAL DEFAULT 0")

# ------------------------------------------------------------
# 3. ضمان وجود باركود مستقل للمنتجات
# ------------------------------------------------------------

ensure_table(con, """
CREATE TABLE IF NOT EXISTS product_barcodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    barcode TEXT NOT NULL,
    is_primary INTEGER DEFAULT 0,
    UNIQUE(barcode)
)
""", "product_barcodes")

# ------------------------------------------------------------
# 4. ضمان وجود بيانات أساسية دون استبدال الموجود
# ------------------------------------------------------------

if table_exists(con, "units"):
    try:
        count = con.execute("SELECT COUNT(*) FROM units").fetchone()[0]
        if count == 0:
            con.execute(
                "INSERT INTO units(name_ar, name_en) VALUES (?,?)",
                ("قطعة", "Piece")
            )
            log("SEED: default unit created")
        else:
            log(f"UNITS EXIST: {count}")
    except Exception as e:
        log(f"UNITS SEED SKIPPED: {e}")

if table_exists(con, "product_categories"):
    try:
        count = con.execute(
            "SELECT COUNT(*) FROM product_categories"
        ).fetchone()[0]
        log(f"CATEGORIES: {count}")
    except Exception as e:
        log(f"CATEGORIES CHECK SKIPPED: {e}")

# ------------------------------------------------------------
# 5. معالجة الباركودات المفقودة دون اختراع باركودات تجارية
# ------------------------------------------------------------

if table_exists(con, "products") and table_exists(con, "product_barcodes"):
    try:
        total_products = con.execute(
            "SELECT COUNT(*) FROM products"
        ).fetchone()[0]
        products_with_barcode = con.execute("""
            SELECT COUNT(DISTINCT product_id)
            FROM product_barcodes
        """).fetchone()[0]

        log(
            f"PRODUCTS: {total_products} | "
            f"PRODUCTS WITH BARCODE: {products_with_barcode}"
        )

        # لا ننشئ باركودات وهمية.
        # نترك المنتجات التي لا تملك باركودًا كما هي.
        log("BARCODE POLICY: no synthetic commercial barcodes generated")
    except Exception as e:
        log(f"BARCODE CHECK SKIPPED: {e}")

# ------------------------------------------------------------
# 6. فحص أرصدة المخزون
# ------------------------------------------------------------

for table in ("stock", "stock_balances"):
    if table_exists(con, table):
        try:
            count = con.execute(
                f'SELECT COUNT(*) FROM "{table}"'
            ).fetchone()[0]
            log(f"{table.upper()}: {count}")
        except Exception as e:
            log(f"{table.upper()} CHECK SKIPPED: {e}")

# ------------------------------------------------------------
# 7. فحص المحاسبة
# ------------------------------------------------------------

if table_exists(con, "journal_entry_lines"):
    try:
        debit = con.execute(
            "SELECT COALESCE(SUM(debit),0) FROM journal_entry_lines"
        ).fetchone()[0]
        credit = con.execute(
            "SELECT COALESCE(SUM(credit),0) FROM journal_entry_lines"
        ).fetchone()[0]

        log(f"ACCOUNTING DEBIT: {debit}")
        log(f"ACCOUNTING CREDIT: {credit}")

        if abs(float(debit or 0) - float(credit or 0)) < 0.01:
            log("ACCOUNTING: BALANCED")
        else:
            log("ACCOUNTING: REVIEW_REQUIRED")
    except Exception as e:
        log(f"ACCOUNTING CHECK SKIPPED: {e}")

# ------------------------------------------------------------
# 8. سلامة قاعدة البيانات
# ------------------------------------------------------------

try:
    con.commit()

    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    fk = con.execute("PRAGMA foreign_key_check").fetchall()

    log(f"INTEGRITY: {integrity}")
    log(f"FOREIGN_KEYS: {fk}")

    if integrity != "ok" or fk:
        log("DATABASE STATUS: REVIEW_REQUIRED")
    else:
        log("DATABASE STATUS: SAFE")
except Exception as e:
    con.rollback()
    log(f"COMMIT/CHECK ERROR: {e}")

# ------------------------------------------------------------
# 9. إحصائية نهائية
# ------------------------------------------------------------

try:
    tables = con.execute("""
        SELECT COUNT(*)
        FROM sqlite_master
        WHERE type='table'
    """).fetchone()[0]
    log(f"TABLE COUNT: {tables}")
except Exception as e:
    log(f"TABLE COUNT ERROR: {e}")

con.close()

report.write_text("\n".join(lines), encoding="utf-8")

print("=" * 70)
print("STAGE STATUS: COMPREHENSIVE REPAIR COMPLETE")
print(f"REPORT: {report}")
print("PowerShell سيبقى مفتوحًا.")
print("=" * 70)
