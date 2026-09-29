from sqlalchemy import text
from app.database.connection import get_session
class SystemValidationService:
 @staticmethod
 def run():
  checks=[]
  with get_session() as s:
   c=s.connection();integrity=c.exec_driver_sql("PRAGMA integrity_check").scalar();checks.append(("سلامة SQLite",integrity=="ok",str(integrity)))
   fk=c.exec_driver_sql("PRAGMA foreign_key_check").fetchall();checks.append(("المفاتيح الأجنبية",not fk,f"{len(fk)} أخطاء"))
   tables={r[0] for r in c.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
   for t in ["products","customers","suppliers","sales","sale_items","purchase_invoices","purchase_invoice_items","stock","stock_movements","accounts","journal_entries","journal_entry_lines","audit_logs"]:checks.append((f"جدول {t}",t in tables,"موجود" if t in tables else "مفقود"))
   if "journal_entries" in tables and "journal_entry_lines" in tables:
    bad=c.exec_driver_sql("SELECT je.id FROM journal_entries je JOIN journal_entry_lines jl ON jl.journal_entry_id=je.id WHERE je.status='POSTED' GROUP BY je.id HAVING ABS(SUM(jl.debit)-SUM(jl.credit))>0.01").fetchall();checks.append(("توازن القيود المرحّلة",not bad,f"{len(bad)} قيود غير متوازنة"))
   if "sales" in tables:
    dup=c.exec_driver_sql("SELECT invoice_number FROM sales GROUP BY invoice_number HAVING COUNT(*)>1").fetchall();checks.append(("أرقام فواتير البيع",not dup,f"{len(dup)} مكررة"))
  return {"healthy":all(x[1] for x in checks),"checks":[{"name":x[0],"ok":x[1],"detail":x[2]} for x in checks]}
