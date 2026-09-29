from decimal import Decimal
from sqlalchemy import text
from app.database.connection import get_session
from app.services.audit_service import AuditService
from app.services.inventory_operations_service import InventoryOperationsService

class StocktakeService:
    @staticmethod
    def _ensure(s):
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS stocktakes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                warehouse_id INTEGER NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
                notes VARCHAR(500),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME
            )
        """))
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS stocktake_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stocktake_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                system_quantity NUMERIC NOT NULL DEFAULT 0,
                counted_quantity NUMERIC NOT NULL DEFAULT 0,
                difference NUMERIC NOT NULL DEFAULT 0,
                UNIQUE(stocktake_id, product_id)
            )
        """))

    @classmethod
    def create(cls, warehouse_id=1, notes=None):
        with get_session() as s:
            cls._ensure(s)
            r=s.execute(text("""
                INSERT INTO stocktakes(warehouse_id,status,notes)
                VALUES(:w,'DRAFT',:n)
            """),{"w":warehouse_id,"n":notes}).lastrowid
            s.commit()
            return int(r)

    @classmethod
    def add_count(cls, stocktake_id, product_id, counted_quantity):
        q=Decimal(str(counted_quantity))
        if q<0: raise ValueError("الكمية المعدودة لا يمكن أن تكون سالبة")
        with get_session() as s:
            cls._ensure(s)
            st=s.execute(text("SELECT warehouse_id,status FROM stocktakes WHERE id=:id"),{"id":stocktake_id}).fetchone()
            if not st: raise ValueError("الجرد غير موجود")
            if st.status!="DRAFT": raise ValueError("الجرد مغلق")
            row=s.execute(text("""
                SELECT COALESCE(quantity,0) FROM stock
                WHERE product_id=:p AND warehouse_id=:w
            """),{"p":product_id,"w":st.warehouse_id}).fetchone()
            system=Decimal(str((row[0] if row else 0) or 0))
            diff=q-system
            s.execute(text("""
                INSERT INTO stocktake_items(stocktake_id,product_id,system_quantity,counted_quantity,difference)
                VALUES(:st,:p,:sys,:cnt,:dif)
                ON CONFLICT(stocktake_id,product_id) DO UPDATE SET
                counted_quantity=excluded.counted_quantity,
                difference=excluded.difference
            """),{"st":stocktake_id,"p":product_id,"sys":float(system),"cnt":float(q),"dif":float(diff)})
            s.commit()
            return {"system_quantity":float(system),"counted_quantity":float(q),"difference":float(diff)}

    @classmethod
    def finalize(cls, stocktake_id, reason="إقفال الجرد"):
        with get_session() as s:
            cls._ensure(s)
            st=s.execute(text("SELECT warehouse_id,status FROM stocktakes WHERE id=:id"),{"id":stocktake_id}).fetchone()
            if not st: raise ValueError("الجرد غير موجود")
            if st.status!="DRAFT": raise ValueError("الجرد مغلق مسبقًا")
            items=s.execute(text("SELECT product_id,counted_quantity FROM stocktake_items WHERE stocktake_id=:id"),{"id":stocktake_id}).fetchall()
            for item in items:
                InventoryOperationsService.adjust(item.product_id,st.warehouse_id,item.counted_quantity,reason)
            # adjust يفتح جلسة مستقلة؛ نعيد حالة الجرد بعد نجاح كل التسويات.
            s.execute(text("""
                UPDATE stocktakes SET status='COMPLETED',completed_at=CURRENT_TIMESTAMP WHERE id=:id
            """),{"id":stocktake_id})
            AuditService.log(s,"STOCKTAKE_COMPLETED","stocktake",stocktake_id)
            s.commit()
            return {"id":stocktake_id,"items":len(items),"status":"COMPLETED"}
