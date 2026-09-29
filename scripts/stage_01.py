from pathlib import Path
import sqlite3
import json
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]

DB_DIR = ROOT / "database"
DB_DIR.mkdir(parents=True, exist_ok=True)

DB = DB_DIR / "nizam_alqirtasiyah.db"

conn = sqlite3.connect(DB)
conn.execute("PRAGMA foreign_keys = ON")

schema = """

CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL,
    tax_number VARCHAR(100),
    phone VARCHAR(50),
    email VARCHAR(200),
    address VARCHAR(500),
    country VARCHAR(100) DEFAULT 'المملكة العربية السعودية',
    city VARCHAR(100) DEFAULT 'جدة',
    currency_code VARCHAR(10) DEFAULT 'SAR',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS branches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    name VARCHAR(200) NOT NULL,
    code VARCHAR(50) NOT NULL UNIQUE,
    phone VARCHAR(50),
    address VARCHAR(500),
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(company_id) REFERENCES companies(id)
);

CREATE TABLE IF NOT EXISTS units (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    symbol VARCHAR(30),
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS currencies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(10) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    symbol VARCHAR(20),
    decimal_places INTEGER NOT NULL DEFAULT 2,
    is_base INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS system_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key VARCHAR(200) NOT NULL UNIQUE,
    setting_value TEXT,
    value_type VARCHAR(30) NOT NULL DEFAULT 'text',
    description VARCHAR(500),
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS document_sequences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    branch_id INTEGER,
    document_type VARCHAR(100) NOT NULL,
    prefix VARCHAR(50) DEFAULT '',
    current_number INTEGER NOT NULL DEFAULT 0,
    padding INTEGER NOT NULL DEFAULT 6,
    UNIQUE(branch_id, document_type),
    FOREIGN KEY(branch_id) REFERENCES branches(id)
);

CREATE TABLE IF NOT EXISTS schema_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stage_number INTEGER NOT NULL,
    version VARCHAR(50) NOT NULL,
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stage_number)
);

"""

conn.executescript(schema)

# ------------------------------------------------------------
# الشركة
# ------------------------------------------------------------

company = conn.execute(
    """
    SELECT id
    FROM companies
    WHERE name = ?
    LIMIT 1
    """,
    ("قرطاسية لؤلؤة الأربعين النموذجية",)
).fetchone()

if company:
    company_id = company[0]
else:
    cursor = conn.execute(
        """
        INSERT INTO companies
        (
            name,
            tax_number,
            phone,
            address,
            country,
            city,
            currency_code
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "قرطاسية لؤلؤة الأربعين النموذجية",
            "",
            "",
            "حي الصفا، شارع عبدالله بن سهل، جدة",
            "المملكة العربية السعودية",
            "جدة",
            "SAR"
        )
    )

    company_id = cursor.lastrowid

# ------------------------------------------------------------
# الفرع الرئيسي
# ------------------------------------------------------------

branch = conn.execute(
    """
    SELECT id
    FROM branches
    WHERE code = ?
    LIMIT 1
    """,
    ("MAIN",)
).fetchone()

if not branch:
    conn.execute(
        """
        INSERT INTO branches
        (
            company_id,
            name,
            code,
            address
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            company_id,
            "الفرع الرئيسي",
            "MAIN",
            "حي الصفا، شارع عبدالله بن سهل، جدة"
        )
    )

# ------------------------------------------------------------
# وحدات القياس
# ------------------------------------------------------------

units = [
    ("قطعة", "قطعة"),
    ("كرتون", "كرتون"),
    ("علبة", "علبة"),
    ("كيلوجرام", "كجم"),
    ("متر", "م")
]

for name, symbol in units:
    conn.execute(
        """
        INSERT OR IGNORE INTO units(name, symbol)
        VALUES (?, ?)
        """,
        (name, symbol)
    )

# ------------------------------------------------------------
# العملة الأساسية
# ------------------------------------------------------------

conn.execute(
    """
    INSERT OR IGNORE INTO currencies
    (
        code,
        name,
        symbol,
        decimal_places,
        is_base
    )
    VALUES (?, ?, ?, ?, ?)
    """,
    (
        "SAR",
        "الريال السعودي",
        "ر.س",
        2,
        1
    )
)

# ------------------------------------------------------------
# إعدادات النظام
# ------------------------------------------------------------

settings = [
    ("system_name", "لؤلؤة ERP", "text"),
    ("language", "ar", "text"),
    ("direction", "rtl", "text"),
    ("country", "SA", "text"),
    ("base_currency", "SAR", "text"),
    ("tax_enabled", "1", "boolean"),
    ("default_tax_rate", "15", "number"),
    ("offline_first", "1", "boolean")
]

for key, value, value_type in settings:
    conn.execute(
        """
        INSERT OR IGNORE INTO system_settings
        (
            setting_key,
            setting_value,
            value_type
        )
        VALUES (?, ?, ?)
        """,
        (key, value, value_type)
    )

# ------------------------------------------------------------
# تسلسلات المستندات
# ------------------------------------------------------------

document_types = [
    "SALE",
    "PURCHASE",
    "PURCHASE_REQUEST",
    "PURCHASE_ORDER",
    "GOODS_RECEIPT",
    "PURCHASE_INVOICE",
    "SALE_RETURN",
    "PURCHASE_RETURN",
    "PRINTING_ORDER",
    "PAYMENT",
    "RECEIPT"
]

branch_id = conn.execute(
    """
    SELECT id
    FROM branches
    WHERE code = ?
    LIMIT 1
    """,
    ("MAIN",)
).fetchone()[0]

for document_type in document_types:
    conn.execute(
        """
        INSERT OR IGNORE INTO document_sequences
        (
            branch_id,
            document_type,
            prefix,
            current_number,
            padding
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            branch_id,
            document_type,
            "",
            0,
            6
        )
    )

# ------------------------------------------------------------
# تسجيل نسخة المخطط
# ------------------------------------------------------------

conn.execute(
    """
    INSERT OR IGNORE INTO schema_versions
    (
        stage_number,
        version
    )
    VALUES (?, ?)
    """,
    (1, "1.0.0")
)

conn.commit()

# ------------------------------------------------------------
# فحص الجداول
# ------------------------------------------------------------

required_tables = [
    "companies",
    "branches",
    "units",
    "currencies",
    "system_settings",
    "document_sequences",
    "schema_versions"
]

existing_tables = {
    row[0]
    for row in conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        """
    ).fetchall()
}

missing = [
    table
    for table in required_tables
    if table not in existing_tables
]

if missing:
    conn.close()
    raise RuntimeError(
        "جداول ناقصة: " + ", ".join(missing)
    )

# ------------------------------------------------------------
# فحص سلامة SQLite
# ------------------------------------------------------------

integrity = conn.execute(
    "PRAGMA integrity_check"
).fetchone()[0]

if integrity != "ok":
    conn.close()
    raise RuntimeError(
        "فشل فحص سلامة قاعدة البيانات: " + str(integrity)
    )

# ------------------------------------------------------------
# التأكد من البيانات الأساسية
# ------------------------------------------------------------

company_count = conn.execute(
    "SELECT COUNT(*) FROM companies"
).fetchone()[0]

branch_count = conn.execute(
    "SELECT COUNT(*) FROM branches"
).fetchone()[0]

currency_count = conn.execute(
    "SELECT COUNT(*) FROM currencies"
).fetchone()[0]

if company_count < 1:
    conn.close()
    raise RuntimeError("لم يتم إنشاء الشركة")

if branch_count < 1:
    conn.close()
    raise RuntimeError("لم يتم إنشاء الفرع")

if currency_count < 1:
    conn.close()
    raise RuntimeError("لم يتم إنشاء العملة")

conn.close()

# ------------------------------------------------------------
# تحديث حالة البناء
# ------------------------------------------------------------

STATE_DIR = ROOT / ".lulu_state"
STATE_DIR.mkdir(parents=True, exist_ok=True)

STATE_FILE = STATE_DIR / "build_state.json"

if STATE_FILE.exists():
    try:
        state = json.loads(
            STATE_FILE.read_text(encoding="utf-8")
        )
    except Exception:
        state = {}
else:
    state = {}

state["project"] = "Nizam_AlQirtasiyah"
state["last_completed_stage"] = 1
state["last_completed_at"] = datetime.now().isoformat()
state["offline_first"] = True

STATE_FILE.write_text(
    json.dumps(
        state,
        ensure_ascii=False,
        indent=2
    ),
    encoding="utf-8"
)

# ------------------------------------------------------------
# سجل تاريخ المراحل
# ------------------------------------------------------------

HISTORY_FILE = STATE_DIR / "build_history.json"

if HISTORY_FILE.exists():
    try:
        history = json.loads(
            HISTORY_FILE.read_text(encoding="utf-8")
        )
    except Exception:
        history = []
else:
    history = []

if not isinstance(history, list):
    history = []

history.append(
    {
        "stage": 1,
        "status": "SUCCESS",
        "completed_at": datetime.now().isoformat(),
        "description": "النظام الأساسي وقاعدة البيانات"
    }
)

HISTORY_FILE.write_text(
    json.dumps(
        history,
        ensure_ascii=False,
        indent=2
    ),
    encoding="utf-8"
)

print("")
print("DATABASE: OK")
print("TABLES: OK")
print("COMPANY: OK")
print("BRANCH: OK")
print("UNITS: OK")
print("CURRENCY: OK")
print("SYSTEM SETTINGS: OK")
print("DOCUMENT SEQUENCES: OK")
print("INTEGRITY: OK")
print("STATE: UPDATED")
print("HISTORY: UPDATED")
print("STATUS: SUCCESS")
