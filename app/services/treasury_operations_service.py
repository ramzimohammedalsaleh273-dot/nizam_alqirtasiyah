from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import text
from app.database.connection import get_session
from app.services.accounting_service import AccountingService
from app.services.audit_service import AuditService
from app.services.document_number_service import DocumentNumberService
from app.services.permission_service import PermissionService


class TreasuryOperationsService:
    """عمليات الخزينة والبنوك الموحدة، مع قيد محاسبي ذري لكل تحويل."""

    @staticmethod
    def money(value):
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def ensure_schema(s):
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
        s.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_treasury_movements_account_date
            ON treasury_movements(treasury_account_id, created_at)
        """))
        s.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_treasury_transfers_source
            ON treasury_transfers(source_account_id, created_at)
        """))
        s.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_treasury_transfers_destination
            ON treasury_transfers(destination_account_id, created_at)
        """))

        # بيانات الخزينة القديمة تُترك كما هي؛ نضيف حسابات تشغيلية فقط عند وجود
        # الحسابات المحاسبية المقابلة.
        for code, name, typ, gl in (
            ("CASH-MAIN", "الصندوق الرئيسي", "CASH", "1100"),
            ("BANK-MAIN", "البنك الرئيسي", "BANK", "1200"),
        ):
            exists = s.execute(text(
                "SELECT 1 FROM treasury_accounts WHERE code=:code"
            ), {"code": code}).fetchone()
            if not exists:
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

    @classmethod
    def _account(cls, s, account_id):
        row = s.execute(text("""
            SELECT id,code,name_ar,account_type,currency_code,gl_account_code,
                   branch_id,opening_balance,is_active
            FROM treasury_accounts WHERE id=:id
        """), {"id": account_id}).mappings().first()
        if not row:
            raise ValueError("حساب الخزينة غير موجود")
        if not row["is_active"]:
            raise ValueError("حساب الخزينة غير نشط")
        return row

    @classmethod
    def _journal_transfer(cls, s, source, destination, amount, number, user_id):
        amount = cls.money(amount)
        debit_id = AccountingService.get_account_id(s, destination["gl_account_code"])
        credit_id = AccountingService.get_account_id(s, source["gl_account_code"])
        entry_number = AccountingService.next_entry_number(s)
        s.execute(text("""
            INSERT INTO journal_entries
            (entry_number,entry_date,description,source_type,source_id,status,
             fiscal_period_id,created_by,created_at)
            VALUES(:n,CURRENT_DATE,:d,'TREASURY_TRANSFER',NULL,'POSTED',NULL,:u,CURRENT_TIMESTAMP)
        """), {
            "n": entry_number,
            "d": f"تحويل خزينة {number}: {source['name_ar']} ← {destination['name_ar']}",
            "u": user_id,
        })
        entry_id = int(s.execute(text("SELECT last_insert_rowid()")).scalar())
        s.execute(text("""
            INSERT INTO journal_entry_lines
            (journal_entry_id,account_id,cost_center_id,description,debit,credit)
            VALUES(:e,:a,NULL,:d,:debit,0)
        """), {
            "e": entry_id, "a": debit_id,
            "d": f"استلام تحويل خزينة {number}",
            "debit": float(amount),
        })
        s.execute(text("""
            INSERT INTO journal_entry_lines
            (journal_entry_id,account_id,cost_center_id,description,debit,credit)
            VALUES(:e,:a,NULL,:d,0,:credit)
        """), {
            "e": entry_id, "a": credit_id,
            "d": f"تحويل صادر من {source['name_ar']} {number}",
            "credit": float(amount),
        })
        return entry_id, entry_number

    @classmethod
    def list_accounts(cls):
        with get_session() as s:
            cls.ensure_schema(s)
            rows = s.execute(text("""
                SELECT id,code,name_ar,account_type,currency_code,gl_account_code,
                       branch_id,is_active
                FROM treasury_accounts
                WHERE is_active=1
                ORDER BY account_type, id
            """)).mappings().all()
            s.commit()
            return [dict(r) for r in rows]

    @classmethod
    def balance(cls, account_id):
        with get_session() as s:
            cls.ensure_schema(s)
            account = cls._account(s, account_id)
            row = s.execute(text("""
                SELECT COALESCE(SUM(jl.debit-jl.credit),0)
                FROM journal_entry_lines jl
                JOIN journal_entries je ON je.id=jl.journal_entry_id
                JOIN accounts a ON a.id=jl.account_id
                WHERE a.account_code=:code
                  AND COALESCE(je.status,'POSTED')='POSTED'
            """), {"code": account["gl_account_code"]}).scalar()
            result = cls.money(account["opening_balance"] or 0)
            result += cls.money(row or 0)
            s.rollback()
            return float(result)

    @classmethod
    def transfer(cls, source_account_id, destination_account_id, amount,
                 user_id=None, notes=None):
        amount = cls.money(amount)
        if amount <= 0:
            raise ValueError("مبلغ التحويل يجب أن يكون أكبر من صفر")
        if int(source_account_id) == int(destination_account_id):
            raise ValueError("لا يمكن التحويل إلى نفس حساب الخزينة")

        with get_session() as s:
            try:
                PermissionService.ensure_schema(s)
                if not PermissionService.has_in_session(
                    s, user_id, "treasury.transfer"
                ):
                    raise PermissionError("لا توجد صلاحية للتحويل بين حسابات الخزينة")

                source = cls._account(s, source_account_id)
                destination = cls._account(s, destination_account_id)

                source_balance = cls.money(source["opening_balance"] or 0) + cls.money(s.execute(text("""
                    SELECT COALESCE(SUM(jl.debit-jl.credit),0)
                    FROM journal_entry_lines jl
                    JOIN journal_entries je ON je.id=jl.journal_entry_id
                    JOIN accounts a ON a.id=jl.account_id
                    WHERE a.account_code=:code AND COALESCE(je.status,'POSTED')='POSTED'
                """), {"code": source["gl_account_code"]}).scalar() or 0)
                if source_balance < amount:
                    raise ValueError(
                        f"الرصيد المتاح في {source['name_ar']} غير كافٍ: {source_balance:.2f}"
                    )

                number = DocumentNumberService.next_number(
                    s, "TREASURY_TRANSFER", "TRF", width=6
                )
                entry_id, _ = cls._journal_transfer(
                    s, source, destination, amount, number, user_id
                )
                transfer_id = int(s.execute(text("""
                    INSERT INTO treasury_transfers
                    (transfer_number,source_account_id,destination_account_id,
                     amount,user_id,journal_entry_id,status,notes)
                    VALUES(:n,:src,:dst,:a,:u,:j,'POSTED',:notes)
                    RETURNING id
                """), {
                    "n": number, "src": source_account_id,
                    "dst": destination_account_id, "a": float(amount),
                    "u": user_id, "j": entry_id, "notes": notes,
                }).scalar())

                for account_id, movement_type, related in (
                    (source_account_id, "TRANSFER_OUT", destination_account_id),
                    (destination_account_id, "TRANSFER_IN", source_account_id),
                ):
                    movement_number = DocumentNumberService.next_number(
                        s, "TREASURY_MOVEMENT", "TMV", width=6
                    )
                    s.execute(text("""
                        INSERT INTO treasury_movements
                        (document_number,treasury_account_id,movement_type,amount,
                         related_account_id,user_id,journal_entry_id,status,notes)
                        VALUES(:n,:a,:t,:amount,:related,:u,:j,'POSTED',:notes)
                    """), {
                        "n": movement_number, "a": account_id,
                        "t": movement_type, "amount": float(amount),
                        "related": related, "u": user_id,
                        "j": entry_id, "notes": notes,
                    })

                AuditService.log(
                    s, "TREASURY_TRANSFER", "treasury_transfer",
                    transfer_id, username=str(user_id) if user_id else None
                )
                s.commit()
                return {
                    "transfer_id": transfer_id,
                    "transfer_number": number,
                    "amount": float(amount),
                    "journal_entry_id": entry_id,
                }
            except Exception:
                s.rollback()
                raise

    @classmethod
    def statement(cls, account_id, limit=100):
        limit = max(1, min(int(limit), 500))
        with get_session() as s:
            cls.ensure_schema(s)
            cls._account(s, account_id)
            rows = s.execute(text(f"""
                SELECT tm.id,tm.document_number,tm.movement_type,tm.amount,
                       tm.reference_number,tm.notes,tm.user_id,tm.journal_entry_id,
                       tm.created_at,ta.name_ar AS related_name
                FROM treasury_movements tm
                LEFT JOIN treasury_accounts ta ON ta.id=tm.related_account_id
                WHERE tm.treasury_account_id=:id
                ORDER BY tm.id DESC
                LIMIT {limit}
            """), {"id": account_id}).mappings().all()
            s.rollback()
            return [dict(r) for r in rows]
