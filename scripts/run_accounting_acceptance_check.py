from sqlalchemy import text
from app.database.connection import get_session
from app.services.accounting_control_service import AccountingControlService


def main():
    with get_session() as s:
        AccountingControlService.ensure_schema(s)
        period = AccountingControlService.ensure_current_period(s)
        s.commit()
        tables = {r[0] for r in s.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()}
        required = {"fiscal_periods", "accounts", "journal_entries", "journal_entry_lines"}
        missing = required - tables
        if missing:
            raise SystemExit(f"FAIL: جداول محاسبية مفقودة: {sorted(missing)}")
        account_cols = {r[1] for r in s.connection().exec_driver_sql("PRAGMA table_info(accounts)").fetchall()}
        journal_cols = {r[1] for r in s.connection().exec_driver_sql("PRAGMA table_info(journal_entries)").fetchall()}
        for col in ("parent_id","account_type","is_group","allow_posting","is_active"):
            if col not in account_cols: raise SystemExit(f"FAIL: accounts.{col} مفقود")
        for col in ("fiscal_period_id","reversed_entry_id","posted_at"):
            if col not in journal_cols: raise SystemExit(f"FAIL: journal_entries.{col} مفقود")
        overlaps = s.execute(text("SELECT COUNT(*) FROM fiscal_periods a JOIN fiscal_periods b ON a.id<b.id AND NOT (a.end_date<b.start_date OR a.start_date>b.end_date)")).scalar() or 0
        unassigned = s.execute(text("SELECT COUNT(*) FROM journal_entries WHERE status='POSTED' AND fiscal_period_id IS NULL")).scalar() or 0
        unbalanced = s.execute(text("""SELECT COUNT(*) FROM (SELECT je.id FROM journal_entries je JOIN journal_entry_lines jl ON jl.journal_entry_id=je.id WHERE je.status='POSTED' GROUP BY je.id HAVING ABS(SUM(COALESCE(jl.debit,0))-SUM(COALESCE(jl.credit,0)))>.01)""")).scalar() or 0
        print("PASS: بنية المحاسبة والفترة الحالية:", period["name_ar"])
        print("PASS: الفترات المتداخلة:", overlaps)
        print("PASS: القيود المرحّلة بلا فترة:", unassigned)
        print("PASS: القيود المرحّلة غير المتوازنة:", unbalanced)
        if overlaps or unassigned or unbalanced: raise SystemExit(1)

if __name__ == "__main__":
    main()
