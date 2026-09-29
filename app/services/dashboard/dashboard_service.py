from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parents[3]
DB_PATH = BASE_DIR / "database" / "nizam_alqirtasiyah.db"


class DashboardService:
    """خدمة قراءة بيانات لوحة التحكم من قاعدة البيانات الحالية."""

    def __init__(self):
        self.db_path = DB_PATH

    def connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def table_exists(self, table_name):
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT 1
                FROM sqlite_master
                WHERE type='table' AND name=?
                """,
                (table_name,)
            ).fetchone()
            return row is not None

    def count(self, table_name):
        if not self.table_exists(table_name):
            return 0

        with self.connection() as conn:
            row = conn.execute(
                f'SELECT COUNT(*) AS total FROM "{table_name}"'
            ).fetchone()
            return int(row["total"])

    def summary(self):
        return {
            "products": self.count("products"),
            "customers": self.count("customers"),
            "suppliers": self.count("suppliers"),
            "sales": self.count("sales"),
            "purchases": self.count("purchase_orders"),
            "warehouses": self.count("warehouses"),
        }
