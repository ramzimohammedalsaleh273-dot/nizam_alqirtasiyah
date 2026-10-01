from decimal import Decimal
from app.database.connection import get_session
from app.services.accounting_service import AccountingService
from app.services.audit_service import AuditService
from app.services.document_number_service import DocumentNumberService
from app.services.reference_compatibility_service import ReferenceCompatibilityService

class ExpenseService:
    @staticmethod
    def list_expenses(limit=500):
        with get_session() as s:
            ReferenceCompatibilityService.ensure(s)
            rows=s.execute(__import__("sqlalchemy").text("""
                SELECT id,expense_number,expense_date,category,description,amount,payment_method,account_id,branch_id,user_id,status,notes
                FROM expenses ORDER BY id DESC LIMIT :limit
            """),{"limit":max(1,min(int(limit),1000))}).mappings().all()
            s.commit()
            return [dict(r) for r in rows]

    @classmethod
    def create(cls, category, description, amount, payment_method="cash", account_id=None, branch_id=None, user_id=None, notes=None):
        amount=AccountingService.money(amount)
        if amount<=0: raise ValueError("قيمة المصروف يجب أن تكون أكبر من صفر")
        with get_session() as s:
            try:
                ReferenceCompatibilityService.ensure(s)
                number=DocumentNumberService.next_number(s,"EXPENSE","EXP",6)
                expense_id=int(s.execute(__import__("sqlalchemy").text("""
                    INSERT INTO expenses(expense_number,expense_date,category,description,amount,payment_method,account_id,branch_id,user_id,status,notes)
                    VALUES(:n,CURRENT_DATE,:c,:d,:a,:m,:acc,:b,:u,'POSTED',:notes) RETURNING id
                """),{"n":number,"c":category,"d":description,"a":float(amount),"m":payment_method,"acc":account_id,"b":branch_id,"u":user_id,"notes":notes}).scalar())
                debit=account_id or AccountingService.get_account_id(s,"5100")
                credit_code=AccountingService.PAYMENT_ACCOUNTS.get(payment_method,"1100")
                credit=AccountingService.get_account_id(s,credit_code)
                posting=AccountingService._post_lines(s,AccountingService.next_entry_number(s),f"مصروف {number}: {category}","EXPENSE",expense_id,[
                    {"account_id":debit,"debit":amount,"credit":Decimal("0"),"description":description or category},
                    {"account_id":credit,"debit":Decimal("0"),"credit":amount,"description":f"دفع مصروف {number}"},
                ])
                AuditService.log(s,"CREATE","expenses",expense_id,username=str(user_id) if user_id else None)
                s.commit()
                return {"id":expense_id,"expense_number":number,"journal_entry_id":posting["journal_entry_id"],"amount":float(amount)}
            except Exception:
                s.rollback(); raise
