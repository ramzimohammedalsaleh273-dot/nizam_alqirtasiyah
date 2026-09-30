from sqlalchemy import text


class TreasurySchemaService:
    """تهيئة وترقية بنية الخزينة التشغيلية بشكل idempotent."""

    @staticmethod
    def _columns(s, table):
        return {row[1] for row in s.connection().exec_driver_sql(
            f"PRAGMA table_info({table})"
        ).fetchall()}

    @classmethod
    def _ensure_column(cls, s, table, column, definition):
        if column not in cls._columns(s, table):
            s.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))

    @classmethod
    def ensure(cls, s):
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS cashier_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cashier_id INTEGER,
                opening_amount NUMERIC(18,2) NOT NULL DEFAULT 0,
                closing_amount NUMERIC(18,2),
                expected_amount NUMERIC(18,2),
                difference NUMERIC(18,2),
                status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
                opened_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                closed_at DATETIME
            )
        """))

        s.execute(text("""
            CREATE TABLE IF NOT EXISTS customer_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                amount NUMERIC(18,2) NOT NULL,
                payment_method VARCHAR(50) NOT NULL DEFAULT 'cash',
                reference_number VARCHAR(100),
                notes VARCHAR(500),
                cashier_session_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS supplier_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier_id INTEGER NOT NULL,
                amount NUMERIC(18,2) NOT NULL,
                payment_method VARCHAR(50) NOT NULL DEFAULT 'cash',
                reference_number VARCHAR(100),
                notes VARCHAR(500),
                cashier_session_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # ترقية قواعد البيانات القديمة: CREATE TABLE IF NOT EXISTS لا يضيف أعمدة.
        if "customer_payments" in cls._table_names(s):
            cls._ensure_column(
                s, "customer_payments", "payment_method",
                "VARCHAR(50) NOT NULL DEFAULT 'cash'"
            )
            cls._ensure_column(
                s, "customer_payments", "reference_number", "VARCHAR(100)"
            )
            cls._ensure_column(
                s, "customer_payments", "notes", "VARCHAR(500)"
            )
            cls._ensure_column(
                s, "customer_payments", "cashier_session_id", "INTEGER"
            )
            cls._ensure_column(
                s, "customer_payments", "created_at",
                "DATETIME DEFAULT CURRENT_TIMESTAMP"
            )

        if "supplier_payments" in cls._table_names(s):
            cls._ensure_column(
                s, "supplier_payments", "payment_method",
                "VARCHAR(50) NOT NULL DEFAULT 'cash'"
            )
            cls._ensure_column(
                s, "supplier_payments", "reference_number", "VARCHAR(100)"
            )
            cls._ensure_column(
                s, "supplier_payments", "notes", "VARCHAR(500)"
            )
            cls._ensure_column(
                s, "supplier_payments", "cashier_session_id", "INTEGER"
            )
            cls._ensure_column(
                s, "supplier_payments", "created_at",
                "DATETIME DEFAULT CURRENT_TIMESTAMP"
            )

        s.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_customer_payments_customer
            ON customer_payments(customer_id)
        """))
        s.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_customer_payments_session
            ON customer_payments(cashier_session_id)
        """))
        s.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_supplier_payments_supplier
            ON supplier_payments(supplier_id)
        """))
        s.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_supplier_payments_session
            ON supplier_payments(cashier_session_id)
        """))
        s.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_cashier_sessions_cashier_status
            ON cashier_sessions(cashier_id,status)
        """))

    @staticmethod
    def _table_names(s):
        return {
            row[0] for row in s.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )).fetchall()
        }
