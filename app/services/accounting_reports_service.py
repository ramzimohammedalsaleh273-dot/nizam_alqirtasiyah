from sqlalchemy import text
from app.database.connection import get_session
from app.services.accounting_control_service import AccountingControlService


class AccountingReportsService:
    """تقارير مالية من القيود المرحلة مع دعم الفترات والحسابات الهرمية."""

    @staticmethod
    def _rows(sql, params=None):
        with get_session() as s:
            return [dict(r._mapping) for r in s.execute(text(sql), params or {}).fetchall()]

    @classmethod
    def trial_balance(cls, period_id=None, as_of=None):
        params={"period_id":period_id,"as_of":as_of}
        period_filter=" AND (:period_id IS NULL OR je.fiscal_period_id=:period_id)"
        date_filter=" AND (:as_of IS NULL OR date(je.entry_date)<=date(:as_of))"
        return cls._rows(f"""
            SELECT a.id,a.account_code AS code,a.name_ar,a.account_type,a.parent_id,
                   COALESCE(SUM(jl.debit),0) debit,COALESCE(SUM(jl.credit),0) credit,
                   COALESCE(SUM(jl.debit-jl.credit),0) balance
            FROM accounts a
            LEFT JOIN journal_entry_lines jl ON jl.account_id=a.id
            LEFT JOIN journal_entries je ON je.id=jl.journal_entry_id AND je.status='POSTED'{period_filter}{date_filter}
            WHERE a.is_active=1
            GROUP BY a.id,a.account_code,a.name_ar,a.account_type,a.parent_id
            ORDER BY a.account_code
        """,params)

    @classmethod
    def general_ledger(cls, account_id=None, start_date=None, end_date=None, period_id=None, limit=1000):
        limit=max(1,min(int(limit),5000)); p={"account_id":account_id,"start_date":start_date,"end_date":end_date,"period_id":period_id,"limit":limit}
        return cls._rows("""
            SELECT je.id AS journal_entry_id,je.entry_number,je.entry_date,je.description,
                   je.source_type,je.source_id,je.fiscal_period_id,a.id AS account_id,
                   a.account_code AS code,a.name_ar,jl.description AS line_description,
                   jl.debit,jl.credit
            FROM journal_entry_lines jl
            JOIN journal_entries je ON je.id=jl.journal_entry_id
            JOIN accounts a ON a.id=jl.account_id
            WHERE je.status='POSTED'
              AND (:account_id IS NULL OR jl.account_id=:account_id)
              AND (:start_date IS NULL OR date(je.entry_date)>=date(:start_date))
              AND (:end_date IS NULL OR date(je.entry_date)<=date(:end_date))
              AND (:period_id IS NULL OR je.fiscal_period_id=:period_id)
            ORDER BY date(je.entry_date),je.id,jl.id
            LIMIT :limit
        """,p)

    @classmethod
    def account_statement(cls, account_id, start_date=None, end_date=None, period_id=None):
        rows=cls.general_ledger(account_id,start_date,end_date,period_id,5000)
        running=0.0
        for row in rows:
            running += float(row.get("debit") or 0)-float(row.get("credit") or 0)
            row["running_balance"]=round(running,2)
        return rows

    @classmethod
    def income_statement(cls, start_date=None, end_date=None, period_id=None):
        p={"start_date":start_date,"end_date":end_date,"period_id":period_id}
        return cls._rows("""
            SELECT a.id,a.account_code AS code,a.name_ar,a.account_type,
                   COALESCE(SUM(jl.credit-jl.debit),0) balance
            FROM accounts a JOIN journal_entry_lines jl ON jl.account_id=a.id
            JOIN journal_entries je ON je.id=jl.journal_entry_id
            WHERE je.status='POSTED' AND a.is_active=1
              AND (a.account_code LIKE '4%' OR a.account_code LIKE '5%')
              AND (:start_date IS NULL OR date(je.entry_date)>=date(:start_date))
              AND (:end_date IS NULL OR date(je.entry_date)<=date(:end_date))
              AND (:period_id IS NULL OR je.fiscal_period_id=:period_id)
            GROUP BY a.id,a.account_code,a.name_ar,a.account_type ORDER BY a.account_code
        """,p)

    @classmethod
    def balance_sheet(cls, as_of=None, period_id=None):
        p={"as_of":as_of,"period_id":period_id}
        return cls._rows("""
            SELECT a.id,a.account_code AS code,a.name_ar,a.account_type,
                   COALESCE(SUM(jl.debit-jl.credit),0) balance
            FROM accounts a JOIN journal_entry_lines jl ON jl.account_id=a.id
            JOIN journal_entries je ON je.id=jl.journal_entry_id
            WHERE je.status='POSTED' AND a.is_active=1
              AND (a.account_code LIKE '1%' OR a.account_code LIKE '2%' OR a.account_code LIKE '3%')
              AND (:as_of IS NULL OR date(je.entry_date)<=date(:as_of))
              AND (:period_id IS NULL OR je.fiscal_period_id=:period_id)
            GROUP BY a.id,a.account_code,a.name_ar,a.account_type ORDER BY a.account_code
        """,p)

    @classmethod
    def journal_report(cls, start_date=None, end_date=None, period_id=None, limit=2000):
        p={"start_date":start_date,"end_date":end_date,"period_id":period_id,"limit":max(1,min(int(limit),10000))}
        return cls._rows("""
            SELECT je.id,je.entry_number,je.entry_date,je.description,je.source_type,je.source_id,
                   je.status,je.fiscal_period_id,a.account_code AS code,a.name_ar,
                   jl.debit,jl.credit,jl.description AS line_description
            FROM journal_entries je JOIN journal_entry_lines jl ON jl.journal_entry_id=je.id
            JOIN accounts a ON a.id=jl.account_id
            WHERE je.status='POSTED'
              AND (:start_date IS NULL OR date(je.entry_date)>=date(:start_date))
              AND (:end_date IS NULL OR date(je.entry_date)<=date(:end_date))
              AND (:period_id IS NULL OR je.fiscal_period_id=:period_id)
            ORDER BY date(je.entry_date),je.id,jl.id LIMIT :limit
        """,p)

    @classmethod
    def cash_flow_summary(cls, start_date=None, end_date=None, period_id=None):
        rows=cls._rows("""
            SELECT a.account_type,a.account_code AS code,a.name_ar,
                   COALESCE(SUM(jl.debit-jl.credit),0) balance
            FROM journal_entry_lines jl JOIN journal_entries je ON je.id=jl.journal_entry_id
            JOIN accounts a ON a.id=jl.account_id
            WHERE je.status='POSTED' AND (a.account_code LIKE '11%' OR a.account_code LIKE '12%')
              AND (:start_date IS NULL OR date(je.entry_date)>=date(:start_date))
              AND (:end_date IS NULL OR date(je.entry_date)<=date(:end_date))
              AND (:period_id IS NULL OR je.fiscal_period_id=:period_id)
            GROUP BY a.id,a.account_type,a.account_code,a.name_ar ORDER BY a.account_code
        """,{"start_date":start_date,"end_date":end_date,"period_id":period_id})
        return rows

    @classmethod
    def fiscal_periods(cls):
        return cls._rows("SELECT id,name_ar,start_date,end_date,status,closed_at,closed_by,notes FROM fiscal_periods ORDER BY start_date DESC")
