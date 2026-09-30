from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import text
from app.services.audit_service import AuditService
from app.services.document_number_service import DocumentNumberService


class AccountingControlService:
    """طبقة المحاسبة الأساسية: دليل الحسابات والفترات والقيود والعكس."""

    @staticmethod
    def money(value):
        return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def _columns(s, table):
        return {r[1] for r in s.connection().exec_driver_sql(f"PRAGMA table_info({table})").fetchall()}

    @classmethod
    def _add_column(cls, s, table, column, definition):
        if column not in cls._columns(s, table):
            s.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))

    @classmethod
    def ensure_schema(cls, s):
        # ترقيات آمنة للجداول القديمة دون حذف أو إعادة إنشاء البيانات.
        cls._add_column(s, "accounts", "parent_id", "INTEGER")
        cls._add_column(s, "accounts", "account_type", "VARCHAR(30) NOT NULL DEFAULT 'ASSET'")
        cls._add_column(s, "accounts", "is_group", "INTEGER NOT NULL DEFAULT 0")
        cls._add_column(s, "accounts", "allow_posting", "INTEGER NOT NULL DEFAULT 1")
        cls._add_column(s, "accounts", "is_active", "INTEGER NOT NULL DEFAULT 1")
        cls._add_column(s, "accounts", "normal_balance", "VARCHAR(10)")
        cls._add_column(s, "accounts", "name_en", "VARCHAR(200)")
        cls._add_column(s, "journal_entries", "fiscal_period_id", "INTEGER")
        cls._add_column(s, "journal_entries", "reversed_entry_id", "INTEGER")
        cls._add_column(s, "journal_entries", "posted_at", "DATETIME")
        cls._add_column(s, "journal_entries", "created_by", "INTEGER")
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS fiscal_periods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name_ar VARCHAR(200) NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
                closed_at DATETIME,
                closed_by INTEGER,
                notes VARCHAR(500),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(start_date,end_date)
            )
        """))
        s.execute(text("CREATE INDEX IF NOT EXISTS ix_accounts_parent ON accounts(parent_id)"))
        s.execute(text("CREATE INDEX IF NOT EXISTS ix_accounts_code ON accounts(account_code)"))
        s.execute(text("CREATE INDEX IF NOT EXISTS ix_journal_entries_period ON journal_entries(fiscal_period_id)"))
        s.execute(text("CREATE INDEX IF NOT EXISTS ix_journal_entries_source ON journal_entries(source_type,source_id)"))

    @classmethod
    def ensure_current_period(cls, s, on_date=None):
        cls.ensure_schema(s)
        d = on_date or date.today()
        row = s.execute(text("""
            SELECT id,name_ar,start_date,end_date,status
            FROM fiscal_periods
            WHERE :d BETWEEN start_date AND end_date
            ORDER BY id DESC LIMIT 1
        """), {"d": d.isoformat()}).mappings().first()
        if row:
            if row["status"] != "OPEN":
                raise ValueError(f"الفترة المالية الحالية مغلقة: {row['name_ar']}")
            return dict(row)
        year = d.year
        name = f"الفترة المالية {year}"
        existing = s.execute(text("SELECT id FROM fiscal_periods WHERE start_date=:a AND end_date=:b"),
                             {"a": f"{year}-01-01", "b": f"{year}-12-31"}).first()
        if existing:
            if s.execute(text("SELECT status FROM fiscal_periods WHERE id=:id"), {"id": existing[0]}).scalar() != "OPEN":
                raise ValueError("الفترة المالية الحالية مغلقة")
            return dict(s.execute(text("SELECT id,name_ar,start_date,end_date,status FROM fiscal_periods WHERE id=:id"), {"id": existing[0]}).mappings().one())
        pid = s.execute(text("""
            INSERT INTO fiscal_periods(name_ar,start_date,end_date,status)
            VALUES(:n,:a,:b,'OPEN') RETURNING id
        """), {"n": name, "a": f"{year}-01-01", "b": f"{year}-12-31"}).scalar()
        return dict(s.execute(text("SELECT id,name_ar,start_date,end_date,status FROM fiscal_periods WHERE id=:id"), {"id": pid}).mappings().one())

    @classmethod
    def create_account(cls, s, code, name_ar, account_type="ASSET", parent_id=None,
                       allow_posting=True, is_group=False, normal_balance=None, name_en=None):
        cls.ensure_schema(s)
        code = str(code).strip()
        if not code or not name_ar:
            raise ValueError("رمز الحساب واسم الحساب مطلوبان")
        if s.execute(text("SELECT 1 FROM accounts WHERE account_code=:c"), {"c": code}).first():
            raise ValueError(f"رمز الحساب موجود مسبقًا: {code}")
        if parent_id is not None:
            p = s.execute(text("SELECT id,is_group,is_active FROM accounts WHERE id=:id"), {"id": parent_id}).mappings().first()
            if not p or not p["is_active"]:
                raise ValueError("الحساب الأب غير موجود أو غير نشط")
            if not p["is_group"]:
                raise ValueError("لا يمكن جعل حساب قابل للترحيل أبًا لحساب آخر")
        aid = s.execute(text("""
            INSERT INTO accounts(account_code,name_ar,account_type,parent_id,allow_posting,is_group,is_active,normal_balance,name_en)
            VALUES(:c,:n,:t,:p,:ap,:g,1,:nb,:ne) RETURNING id
        """), {"c":code,"n":name_ar,"t":account_type,"p":parent_id,"ap":int(bool(allow_posting)),"g":int(bool(is_group)),"nb":normal_balance,"ne":name_en}).scalar()
        AuditService.log(s, "ACCOUNT_CREATE", "account", int(aid))
        return int(aid)

    @classmethod
    def set_posting_allowed(cls, s, account_id, allowed):
        cls.ensure_schema(s)
        row=s.execute(text("SELECT id,is_group FROM accounts WHERE id=:id"),{"id":account_id}).mappings().first()
        if not row: raise ValueError("الحساب غير موجود")
        if allowed and row["is_group"]: raise ValueError("الحساب التجميعي لا يقبل الترحيل")
        s.execute(text("UPDATE accounts SET allow_posting=:v WHERE id=:id"),{"v":int(bool(allowed)),"id":account_id})
        AuditService.log(s,"ACCOUNT_POSTING_CHANGED","account",int(account_id))

    @classmethod
    def create_period(cls, s, name_ar, start_date, end_date):
        cls.ensure_schema(s)
        if str(start_date) > str(end_date): raise ValueError("بداية الفترة يجب أن تسبق نهايتها")
        if s.execute(text("""SELECT 1 FROM fiscal_periods WHERE NOT (end_date < :start_date OR start_date > :end_date) LIMIT 1"""),{"start_date":str(start_date),"end_date":str(end_date)}).first():
            raise ValueError("الفترة تتداخل مع فترة مالية موجودة")
        pid=s.execute(text("INSERT INTO fiscal_periods(name_ar,start_date,end_date,status) VALUES(:n,:a,:b,'OPEN') RETURNING id"),{"n":name_ar,"a":str(start_date),"b":str(end_date)}).scalar()
        AuditService.log(s,"FISCAL_PERIOD_CREATE","fiscal_period",int(pid))
        return int(pid)

    @classmethod
    def close_period(cls, s, period_id, user_id=None, notes=None):
        cls.ensure_schema(s)
        period=s.execute(text("SELECT * FROM fiscal_periods WHERE id=:id"),{"id":period_id}).mappings().first()
        if not period: raise ValueError("الفترة المالية غير موجودة")
        if period["status"] != "OPEN": raise ValueError("الفترة ليست مفتوحة")
        unbalanced=s.execute(text("""SELECT je.id FROM journal_entries je JOIN journal_entry_lines jl ON jl.journal_entry_id=je.id WHERE je.fiscal_period_id=:p AND je.status='POSTED' GROUP BY je.id HAVING ABS(SUM(jl.debit)-SUM(jl.credit))>.01"""),{"p":period_id}).fetchall()
        if unbalanced: raise ValueError("لا يمكن إقفال فترة تحتوي على قيد غير متوازن")
        s.execute(text("UPDATE fiscal_periods SET status='CLOSED',closed_at=CURRENT_TIMESTAMP,closed_by=:u,notes=:n WHERE id=:id"),{"u":user_id,"n":notes,"id":period_id})
        AuditService.log(s,"FISCAL_PERIOD_CLOSE","fiscal_period",int(period_id),str(user_id) if user_id else None)

    @classmethod
    def assert_open_period(cls, s, period_id):
        row=s.execute(text("SELECT status FROM fiscal_periods WHERE id=:id"),{"id":period_id}).first()
        if not row or row[0] != "OPEN": raise ValueError("الفترة المالية مغلقة أو غير موجودة")

    @classmethod
    def post_entry(cls, s, description, lines, entry_date=None, source_type="MANUAL", source_id=None, user_id=None, period_id=None):
        cls.ensure_schema(s)
        period=cls.ensure_current_period(s, entry_date)
        period_id=int(period_id or period["id"])
        cls.assert_open_period(s, period_id)
        if not lines or len(lines)<2: raise ValueError("القيد يحتاج إلى سطرين على الأقل")
        debit=cls.money(sum((cls.money(x.get("debit",0)) for x in lines),Decimal("0")))
        credit=cls.money(sum((cls.money(x.get("credit",0)) for x in lines),Decimal("0")))
        if debit <= 0 or debit != credit: raise ValueError(f"القيد غير متوازن: مدين={debit} دائن={credit}")
        checked=[]
        for x in lines:
            aid=int(x["account_id"])
            a=s.execute(text("SELECT id,allow_posting,is_active,is_group FROM accounts WHERE id=:id"),{"id":aid}).mappings().first()
            if not a or not a["is_active"]: raise ValueError(f"الحساب غير موجود أو غير نشط: {aid}")
            if not a["allow_posting"] or a["is_group"]: raise ValueError(f"الحساب غير قابل للترحيل: {aid}")
            checked.append((aid,cls.money(x.get("debit",0)),cls.money(x.get("credit",0)),x.get("description") or description))
        number=DocumentNumberService.next_number(s,"JOURNAL","JE",width=6)
        eid=s.execute(text("""
            INSERT INTO journal_entries(entry_number,entry_date,description,source_type,source_id,status,fiscal_period_id,created_by,posted_at,created_at)
            VALUES(:n,:d,:desc,:st,:sid,'POSTED',:p,:u,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP) RETURNING id
        """),{"n":number,"d":str(entry_date or date.today()),"desc":description,"st":source_type,"sid":source_id,"p":period_id,"u":user_id}).scalar()
        for aid,de,cr,desc in checked:
            s.execute(text("INSERT INTO journal_entry_lines(journal_entry_id,account_id,cost_center_id,description,debit,credit) VALUES(:e,:a,NULL,:d,:de,:cr)"),{"e":eid,"a":aid,"d":desc,"de":float(de),"cr":float(cr)})
        AuditService.log(s,"JOURNAL_POST","journal_entry",int(eid),str(user_id) if user_id else None)
        return {"id":int(eid),"entry_number":number,"period_id":period_id,"debit":float(debit),"credit":float(credit)}

    @classmethod
    def reverse_entry(cls, s, entry_id, user_id=None, reason=None):
        cls.ensure_schema(s)
        head=s.execute(text("SELECT * FROM journal_entries WHERE id=:id"),{"id":entry_id}).mappings().first()
        if not head: raise ValueError("القيد غير موجود")
        if head["status"] != "POSTED": raise ValueError("لا يمكن عكس قيد غير مرحّل")
        if head["reversed_entry_id"]: raise ValueError("القيد تم عكسه مسبقًا")
        lines=s.execute(text("SELECT account_id,debit,credit,description FROM journal_entry_lines WHERE journal_entry_id=:id ORDER BY id"),{"id":entry_id}).mappings().all()
        period_id=head["fiscal_period_id"]
        if period_id is not None: cls.assert_open_period(s,period_id)
        result=cls.post_entry(s,f"عكس القيد {head['entry_number']}: {reason or ''}",[dict(account_id=x["account_id"],debit=x["credit"],credit=x["debit"],description=f"عكس: {x['description'] or ''}") for x in lines],head["entry_date"],"REVERSAL",int(entry_id),user_id,period_id)
        s.execute(text("UPDATE journal_entries SET reversed_entry_id=:rid WHERE id=:id"),{"rid":result["id"],"id":entry_id})
        AuditService.log(s,"JOURNAL_REVERSE","journal_entry",int(entry_id),str(user_id) if user_id else None)
        return result
