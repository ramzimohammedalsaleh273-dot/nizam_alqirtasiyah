from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import text
from app.database.connection import get_session
from app.services.audit_service import AuditService
from app.services.accounting_service import AccountingService

class SalesReturnService:
    """مرتجع بيع فعلي: يعيد المخزون وينشئ قيدًا عكسيًا، ولا يعبث بالقيد الأصلي."""
    @classmethod
    def create_return(cls,sale_id,items,reason):
        if not items or not reason or not reason.strip(): raise ValueError("بنود المرتجع والسبب مطلوبان")
        with get_session() as s:
            try:
                sale=s.execute(text("SELECT * FROM sales WHERE id=:id"),{"id":sale_id}).fetchone()
                if not sale: raise ValueError("فاتورة البيع غير موجودة")
                if getattr(sale,"status",None) in ("VOID","CANCELLED"): raise ValueError("لا يمكن إرجاع فاتورة ملغاة")
                original=s.execute(text("""SELECT id FROM journal_entries WHERE source_type='SALE' AND source_id=:id AND status='POSTED' ORDER BY id DESC LIMIT 1"""),{"id":sale_id}).fetchone()
                if not original: raise ValueError("القيد الأصلي للفاتورة غير موجود")
                totals={"subtotal":Decimal("0"),"tax":Decimal("0"),"total":Decimal("0"),"cogs":Decimal("0")}
                for x in items:
                    pid=int(x["product_id"]); qty=Decimal(str(x["quantity"]))
                    if qty<=0: raise ValueError("كمية المرتجع يجب أن تكون موجبة")
                    row=s.execute(text("""SELECT quantity,unit_price,discount FROM sale_items WHERE sale_id=:sid AND product_id=:pid LIMIT 1"""),{"sid":sale_id,"pid":pid}).fetchone()
                    if not row: raise ValueError(f"الصنف {pid} غير موجود في الفاتورة")
                    if qty>Decimal(str(row.quantity)): raise ValueError(f"كمية المرتجع أكبر من الكمية المباعة للصنف {pid}")
                    line=(qty*Decimal(str(row.unit_price or 0))-Decimal(str(row.discount or 0))).quantize(Decimal("0.01"),ROUND_HALF_UP)
                    totals["subtotal"]+=line
                    stock=s.execute(text("UPDATE stock SET quantity=quantity+:q,available_quantity=available_quantity+:q,updated_at=CURRENT_TIMESTAMP WHERE product_id=:p AND warehouse_id=:w"),{"q":float(qty),"p":pid,"w":getattr(sale,"warehouse_id",1)})
                    if not stock.rowcount: raise ValueError(f"مخزون الصنف {pid} غير موجود")
                    cols={r[1] for r in s.connection().exec_driver_sql("PRAGMA table_info(stock_movements)").fetchall()}
                    fields=["product_id","warehouse_id","quantity"];vals=[":p",":w",":q"];params={"p":pid,"w":getattr(sale,"warehouse_id",1),"q":float(qty)}
                    for col,val in [("movement_type","RETURN"),("reference_type","SALE_RETURN"),("reference_id",sale_id),("notes",reason)]:
                        if col in cols:fields.append(col);vals.append(":"+col);params[col]=val
                    if "created_at" in cols:fields.append("created_at");vals.append("CURRENT_TIMESTAMP")
                    s.execute(text(f"INSERT INTO stock_movements({','.join(fields)}) VALUES({','.join(vals)})"),params)
                totals["tax"]=(totals["subtotal"]*AccountingService.TAX_RATE).quantize(Decimal("0.01"),ROUND_HALF_UP)
                totals["total"]=(totals["subtotal"]+totals["tax"]).quantize(Decimal("0.01"),ROUND_HALF_UP)
                lines=s.execute(text("SELECT account_id,debit,credit,description FROM journal_entry_lines WHERE journal_entry_id=:id"),{"id":int(original[0])}).fetchall()
                n=AccountingService.next_entry_number(s)
                s.execute(text("""INSERT INTO journal_entries(entry_number,entry_date,description,source_type,source_id,status,fiscal_period_id,created_by,created_at)
                                  VALUES(:n,CURRENT_DATE,:d,'SALE_RETURN',:sid,'POSTED',NULL,NULL,CURRENT_TIMESTAMP)"""),{"n":n,"d":f"مرتجع فاتورة البيع {getattr(sale,'invoice_number','')}: {reason}","sid":sale_id})
                eid=int(s.execute(text("SELECT last_insert_rowid()")).scalar())
                for line in lines:
                    s.execute(text("""INSERT INTO journal_entry_lines(journal_entry_id,account_id,cost_center_id,description,debit,credit)
                                      VALUES(:e,:a,NULL,:d,:debit,:credit)"""),{"e":eid,"a":int(line.account_id),"d":f"عكس مرتجع: {line.description}","debit":float(line.credit or 0),"credit":float(line.debit or 0)})
                AuditService.log(s,"SALE_RETURN","sale",sale_id)
                s.commit()
                return {"sale_id":sale_id,"total":float(totals["total"]),"journal_entry_id":eid}
            except Exception:
                s.rollback();raise
