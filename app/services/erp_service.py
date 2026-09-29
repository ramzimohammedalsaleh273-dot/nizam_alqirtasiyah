import sqlite3
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "database" / "nizam_alqirtasiyah.db"


class ERPDatabase:

    def connect(self):
        con = sqlite3.connect(DB_PATH)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        return con

    def table_exists(self, table):
        with self.connect() as con:
            return con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (table,)
            ).fetchone() is not None

    def columns(self, table):
        with self.connect() as con:
            return [
                row["name"]
                for row in con.execute(f'PRAGMA table_info("{table}")')
            ]

    def count(self, table):
        if not self.table_exists(table):
            return 0
        with self.connect() as con:
            return con.execute(
                f'SELECT COUNT(*) FROM "{table}"'
            ).fetchone()[0]


db = ERPDatabase()


def get_company():
    with db.connect() as con:
        row = con.execute(
            "SELECT * FROM companies ORDER BY id LIMIT 1"
        ).fetchone()
        return dict(row) if row else {}


def get_settings():
    if not db.table_exists("system_settings"):
        return []

    with db.connect() as con:
        rows = con.execute("""
            SELECT
                id,
                setting_key,
                setting_value,
                value_type,
                description,
                updated_at
            FROM system_settings
            ORDER BY setting_key
        """).fetchall()

    return [dict(row) for row in rows]


def get_accounts():
    if not db.table_exists("accounts"):
        return []

    with db.connect() as con:
        rows = con.execute("""
            SELECT
                id,
                account_code,
                account_name,
                account_type,
                parent_id,
                is_active,
                allow_posting,
                opening_balance
            FROM accounts
            ORDER BY account_code
        """).fetchall()

    return [dict(row) for row in rows]


def get_products():
    if not db.table_exists("products"):
        return []

    with db.connect() as con:
        rows = con.execute("""
            SELECT
                id,
                sku,
                name_ar,
                name_en,
                category_id,
                brand_id,
                unit_id,
                product_type,
                cost_price,
                sale_price,
                wholesale_price,
                school_price,
                min_stock,
                max_stock,
                is_active
            FROM products
            ORDER BY id DESC
            LIMIT 500
        """).fetchall()

    return [dict(row) for row in rows]


def get_customers():
    if not db.table_exists("customers"):
        return []

    with db.connect() as con:
        rows = con.execute(
            "SELECT * FROM customers ORDER BY id DESC LIMIT 500"
        ).fetchall()

    return [dict(row) for row in rows]


def get_suppliers():
    if not db.table_exists("suppliers"):
        return []

    with db.connect() as con:
        rows = con.execute(
            "SELECT * FROM suppliers ORDER BY id DESC LIMIT 500"
        ).fetchall()

    return [dict(row) for row in rows]


def get_sales():
    if not db.table_exists("sales"):
        return []

    with db.connect() as con:
        rows = con.execute(
            "SELECT * FROM sales ORDER BY id DESC LIMIT 500"
        ).fetchall()

    return [dict(row) for row in rows]


def get_purchases():
    if not db.table_exists("purchase_orders"):
        return []

    with db.connect() as con:
        rows = con.execute(
            "SELECT * FROM purchase_orders ORDER BY id DESC LIMIT 500"
        ).fetchall()

    return [dict(row) for row in rows]


def get_cash_transactions():
    if not db.table_exists("cash_transactions"):
        return []

    with db.connect() as con:
        rows = con.execute(
            "SELECT * FROM cash_transactions ORDER BY id DESC LIMIT 500"
        ).fetchall()

    return [dict(row) for row in rows]


def get_journal_entries():
    if not db.table_exists("journal_entries"):
        return []

    with db.connect() as con:
        rows = con.execute(
            "SELECT * FROM journal_entries ORDER BY id DESC LIMIT 500"
        ).fetchall()

    return [dict(row) for row in rows]


def get_dashboard():
    tables = [
        "products",
        "customers",
        "suppliers",
        "users",
        "accounts",
        "branches",
        "warehouses",
        "sales",
        "purchase_orders",
        "journal_entries",
        "cash_transactions",
        "notifications"
    ]

    result = {}

    for table in tables:
        result[table] = db.count(table)

    return result


def health_check():
    required = [
        "companies",
        "branches",
        "accounts",
        "products",
        "customers",
        "suppliers",
        "sales",
        "sale_items",
        "purchase_orders",
        "purchase_order_items",
        "journal_entries",
        "journal_entry_lines",
        "cash_transactions",
        "system_settings",
        "users"
    ]

    missing = [
        table for table in required
        if not db.table_exists(table)
    ]

    return {
        "database": str(DB_PATH),
        "missing_tables": missing,
        "status": "OK" if not missing else "INCOMPLETE",
        "checked_at": datetime.now().isoformat()
    }
