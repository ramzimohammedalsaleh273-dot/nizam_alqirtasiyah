from sqlalchemy import text
from app.database.connection import get_session
from app.services.audit_service import AuditService
from app.services.accounting_service import AccountingService

class POSOperationsService:
    @staticmethod
    def _has(s, table, column):
        return column in {r[1] for r in s.connection().exec_driver_sql(f"PRAGMA table_info({table})").fetchall()}

    @classmethod
    def void_sale(cls, sale_id, reason):
        if not reason or not reason.strip():
            raise ValueError("سبب الإلغاء مطلوب")
        with get_session() as s:
            try:
                sale = s.execute(text("SELECT * FROM sales WHERE id=:id"), {"id": sale_id}).fetchone()
                if not sale:
                    raise ValueError("الفاتورة غير موجودة")
                if getattr(sale, "status", None) in ("VOID", "CANCELLED", "RETURNED"):
                    raise ValueError("الفاتورة ملغاة مسبقًا")
                original = s.execute(text("""
                    SELECT id FROM journal_entries
                    WHERE source_type='SALE' AND source_id=:id AND status='POSTED'
                    ORDER BY id DESC LIMIT 1
                """), {"id": sale_id}).fetchone()
                items = s.execute(text("SELECT product_id,quantity FROM sale_items WHERE sale_id=:id"), {"id": sale_id}).fetchall()
                wh = getattr(sale, "warehouse_id", 1)
                for item in items:
                    updated = s.execute(text("""
                        UPDATE stock SET quantity=COALESCE(quantity,0)+:q,
                        available_quantity=COALESCE(available_quantity,0)+:q,
                        updated_at=CURRENT_TIMESTAMP
                        WHERE product_id=:p AND warehouse_id=:w
                    """), {"q": float(item.quantity), "p": item.product_id, "w": wh}).rowcount
                    if not updated:
                        raise ValueError(f"سجل المخزون غير موجود للصنف {item.product_id}")
                    if cls._has(s, "stock_movements", "product_id"):
                        cols = {r[1] for r in s.connection().exec_driver_sql("PRAGMA table_info(stock_movements)").fetchall()}
                        fields=["product_id","warehouse_id","quantity"]; values=[":p",":w",":q"]
                        params={"p":item.product_id,"w":wh,"q":float(item.quantity)}
                        for c,v in [("movement_type","RETURN"),("reference_type","SALE"),("reference_id",sale_id),("notes",reason)]:
                            if c in cols: fields.append(c); values.append(":"+c); params[c]=v
                        if "created_at" in cols: fields.append("created_at"); values.append("CURRENT_TIMESTAMP")
                        s.execute(text(f"INSERT INTO stock_movements({','.join(fields)}) VALUES({','.join(values)})"), params)
                reverse_id = None
                if original:
                    lines = s.execute(text("""
                        SELECT account_id, description, debit, credit
                        FROM journal_entry_lines WHERE journal_entry_id=:id
                    """), {"id": int(original[0])}).fetchall()
                    entry_number = AccountingService.next_entry_number(s)
                    s.execute(text("""
                        INSERT INTO journal_entries
                        (entry_number,entry_date,description,source_type,source_id,status,
                         fiscal_period_id,created_by,created_at)
                        VALUES (:n,CURRENT_DATE,:d,'SALE_VOID',:sid,'POSTED',NULL,NULL,CURRENT_TIMESTAMP)
                    """), {"n":entry_number,"d":f"عكس إلغاء فاتورة البيع {getattr(sale,'invoice_number','')}: {reason}","sid":sale_id})
                    reverse_id=int(s.execute(text("SELECT last_insert_rowid()")).scalar())
                    for line in lines:
                        s.execute(text("""
                            INSERT INTO journal_entry_lines
                            (journal_entry_id,account_id,cost_center_id,description,debit,credit)
                            VALUES (:eid,:aid,NULL,:desc,:debit,:credit)
                        """), {"eid":reverse_id,"aid":int(line.account_id),"desc":f"عكس: {line.description}",
                               "debit":float(line.credit or 0),"credit":float(line.debit or 0)})
                if cls._has(s, "sales", "status"):
                    s.execute(text("UPDATE sales SET status='VOID' WHERE id=:id"), {"id": sale_id})
                AuditService.log(s, "SALE_VOID", "sale", sale_id)
                s.commit()
                return {"sale_id": sale_id, "status": "VOID", "reversal_journal_id": reverse_id}
            except Exception:
                s.rollback()
                raise
