from sqlalchemy import text
from app.database.connection import get_session
class AccountingReportsService:
 @staticmethod
 def _rows(sql,params=None):
  with get_session() as s:return [dict(r._mapping) for r in s.execute(text(sql),params or {}).fetchall()]
 @classmethod
 def trial_balance(cls):return cls._rows("""SELECT a.id,a.code,a.name_ar,COALESCE(SUM(jl.debit),0) debit,COALESCE(SUM(jl.credit),0) credit,COALESCE(SUM(jl.debit-jl.credit),0) balance FROM accounts a LEFT JOIN journal_entry_lines jl ON jl.account_id=a.id LEFT JOIN journal_entries je ON je.id=jl.journal_entry_id AND je.status='POSTED' GROUP BY a.id,a.code,a.name_ar ORDER BY a.code""")
 @classmethod
 def general_ledger(cls,account_id=None,limit=500):
  where="";p={"limit":limit}
  if account_id is not None:where=" AND jl.account_id=:account_id";p["account_id"]=account_id
  return cls._rows(f"""SELECT je.entry_number,je.entry_date,je.description,a.code,a.name_ar,jl.debit,jl.credit FROM journal_entry_lines jl JOIN journal_entries je ON je.id=jl.journal_entry_id JOIN accounts a ON a.id=jl.account_id WHERE je.status='POSTED'{where} ORDER BY je.entry_date DESC,je.id DESC LIMIT :limit""",p)
 @classmethod
 def income_statement(cls):return cls._rows("""SELECT a.code,a.name_ar,COALESCE(SUM(jl.credit-jl.debit),0) balance FROM accounts a JOIN journal_entry_lines jl ON jl.account_id=a.id JOIN journal_entries je ON je.id=jl.journal_entry_id WHERE je.status='POSTED' AND (a.code LIKE '4%' OR a.code LIKE '5%') GROUP BY a.id,a.code,a.name_ar ORDER BY a.code""")
 @classmethod
 def balance_sheet(cls):return cls._rows("""SELECT a.code,a.name_ar,COALESCE(SUM(jl.debit-jl.credit),0) balance FROM accounts a JOIN journal_entry_lines jl ON jl.account_id=a.id JOIN journal_entries je ON je.id=jl.journal_entry_id WHERE je.status='POSTED' AND (a.code LIKE '1%' OR a.code LIKE '2%' OR a.code LIKE '3%') GROUP BY a.id,a.code,a.name_ar ORDER BY a.code""")
