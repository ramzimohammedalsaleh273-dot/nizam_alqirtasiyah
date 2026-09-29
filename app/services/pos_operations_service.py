from sqlalchemy import text
from app.database.connection import get_session
from app.services.audit_service import AuditService
class POSOperationsService:
 @staticmethod
 def _has(s,t,c):return c in {r[1] for r in s.connection().exec_driver_sql(f"PRAGMA table_info({t})").fetchall()}
 @classmethod
 def void_sale(cls,sale_id,reason):
  if not reason or not reason.strip():raise ValueError("سبب الإلغاء مطلوب")
  with get_session() as s:
   try:
    sale=s.execute(text("SELECT * FROM sales WHERE id=:id"),{"id":sale_id}).fetchone()
    if not sale:raise ValueError("الفاتورة غير موجودة")
    if getattr(sale,"status",None) in ("VOID","CANCELLED","RETURNED"):raise ValueError("الفاتورة ملغاة مسبقًا")
    items=s.execute(text("SELECT product_id,quantity FROM sale_items WHERE sale_id=:id"),{"id":sale_id}).fetchall()
    wh=getattr(sale,"warehouse_id",1)
    for it in items:
     s.execute(text("UPDATE stock SET quantity=quantity+:q,available_quantity=available_quantity+:q,updated_at=CURRENT_TIMESTAMP WHERE product_id=:p AND warehouse_id=:w"),{"q":float(it.quantity),"p":it.product_id,"w":wh})
     if cls._has(s,"stock_movements","product_id"):
      s.execute(text("INSERT INTO stock_movements(product_id,warehouse_id,movement_type,quantity,reference_type,reference_id,notes,created_at) VALUES(:p,:w,'RETURN',:q,'SALE',:id,:n,CURRENT_TIMESTAMP)"),{"p":it.product_id,"w":wh,"q":float(it.quantity),"id":sale_id,"n":reason})
    if cls._has(s,"sales","status"):s.execute(text("UPDATE sales SET status='VOID' WHERE id=:id"),{"id":sale_id})
    AuditService.log(s,"SALE_VOID","sale",sale_id);s.commit()
   except Exception:s.rollback();raise
