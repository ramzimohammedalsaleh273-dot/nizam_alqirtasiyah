from sqlalchemy import text


class TreasurySchemaService:
    """تهيئة وترقية بنية الخزينة التشغيلية بشكل متوافق مع قواعد البيانات القديمة."""

    @staticmethod
    def _columns(s, table):
        return {row[1] for row in s.connection().exec_driver_sql(
            f"PRAGMA table_info({table})"
        ).fetchall()}

    @classmethod
    def _ensure_column(cls, s, table, column, definition):
        if column not in cls._columns(s, table):
            s.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))

    @staticmethod
    def _table_names(s):
        return {
            row[0] for row in s.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )).fetchall()
        }

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
        for column, definition in (
            ("opened_by", "INTEGER"),
            ("closed_by", "INTEGER"),
            ("close_notes", "VARCHAR(500)"),
        ):
            cls._ensure_column(s, "cashier_sessions", column, definition)

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

        for table in ("customer_payments", "supplier_payments"):
            if table in cls._table_names(s):
                for column, definition in (
                    ("payment_method", "VARCHAR(50) NOT NULL DEFAULT 'cash'"),
                    ("reference_number", "VARCHAR(100)"),
                    ("notes", "VARCHAR(500)"),
                    ("cashier_session_id", "INTEGER"),
                    ("created_at", "DATETIME DEFAULT CURRENT_TIMESTAMP"),
                ):
                    cls._ensure_column(s, table, column, definition)

        s.execute(text("""
            CREATE TABLE IF NOT EXISTS treasury_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code VARCHAR(80) NOT NULL UNIQUE,
                name_ar VARCHAR(200) NOT NULL,
                account_type VARCHAR(20) NOT NULL,
                currency_code VARCHAR(10) NOT NULL DEFAULT 'SAR',
                gl_account_code VARCHAR(80) NOT NULL,
                branch_id INTEGER,
                opening_balance NUMERIC(18,2) NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS bank_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                treasury_account_id INTEGER NOT NULL UNIQUE,
                bank_name VARCHAR(200) NOT NULL,
                account_number VARCHAR(100),
                iban VARCHAR(100),
                swift_code VARCHAR(50),
                notes VARCHAR(500),
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS cash_registers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                treasury_account_id INTEGER NOT NULL UNIQUE,
                name_ar VARCHAR(200) NOT NULL,
                cashier_id INTEGER,
                branch_id INTEGER,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS treasury_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_number VARCHAR(100) NOT NULL UNIQUE,
                treasury_account_id INTEGER NOT NULL,
                movement_type VARCHAR(30) NOT NULL,
                amount NUMERIC(18,2) NOT NULL,
                related_account_id INTEGER,
                cashier_session_id INTEGER,
                reference_number VARCHAR(100),
                notes VARCHAR(500),
                user_id INTEGER,
                journal_entry_id INTEGER,
                status VARCHAR(20) NOT NULL DEFAULT 'POSTED',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS treasury_transfers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transfer_number VARCHAR(100) NOT NULL UNIQUE,
                source_account_id INTEGER NOT NULL,
                destination_account_id INTEGER NOT NULL,
                amount NUMERIC(18,2) NOT NULL,
                user_id INTEGER,
                journal_entry_id INTEGER,
                status VARCHAR(20) NOT NULL DEFAULT 'POSTED',
                notes VARCHAR(500),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))

        for sql in (
            "CREATE INDEX IF NOT EXISTS ix_customer_payments_customer ON customer_payments(customer_id)",
            "CREATE INDEX IF NOT EXISTS ix_customer_payments_session ON customer_payments(cashier_session_id)",
            "CREATE INDEX IF NOT EXISTS ix_supplier_payments_supplier ON supplier_payments(supplier_id)",
            "CREATE INDEX IF NOT EXISTS ix_supplier_payments_session ON supplier_payments(cashier_session_id)",
            "CREATE INDEX IF NOT EXISTS ix_cashier_sessions_cashier_status ON cashier_sessions(cashier_id,status)",
            "CREATE INDEX IF NOT EXISTS ix_treasury_movements_account_date ON treasury_movements(treasury_account_id,created_at)",
            "CREATE INDEX IF NOT EXISTS ix_treasury_transfers_source ON treasury_transfers(source_account_id,created_at)",
            "CREATE INDEX IF NOT EXISTS ix_treasury_transfers_destination ON treasury_transfers(destination_account_id,created_at)",
        ):
            s.execute(text(sql))

        # حسابات تشغيلية مرتبطة مباشرة بدليل الحسابات؛ لا ننشئها إذا كان
        # الحساب المحاسبي المقابل غير موجود حتى لا نخلق بيانات وهمية.
        for code, name, typ, gl in (
            ("CASH-MAIN", "الصندوق الرئيسي", "CASH", "1100"),
            ("BANK-MAIN", "البنك الرئيسي", "BANK", "1200"),
        ):
            exists = s.execute(text(
                "SELECT 1 FROM treasury_accounts WHERE code=:code"
            ), {"code": code}).fetchone()
            if not exists:
                table_exists = s.execute(text("SELECT 1 FROM sqlite_master WHERE type='table' AND name='accounts'")).scalar()
                if not table_exists:
                    continue
                gl_exists = s.execute(text("""
                    SELECT 1 FROM accounts
                    WHERE account_code=:gl AND is_active=1 AND allow_posting=1
                    LIMIT 1
                """), {"gl": gl}).fetchone()
                if gl_exists:
                    s.execute(text("""
                        INSERT INTO treasury_accounts
                        (code,name_ar,account_type,currency_code,gl_account_code)
                        VALUES(:code,:name,:typ,'SAR',:gl)
                    """), {"code": code, "name": name, "typ": typ, "gl": gl})
