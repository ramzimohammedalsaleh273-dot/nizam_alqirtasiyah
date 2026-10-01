from decimal import Decimal
from sqlalchemy import text
from app.database.connection import get_session
from app.services.audit_service import AuditService
from app.services.permission_service import PermissionService

class InventoryOperationsService:
    @staticmethod
    def _cols(s,t): return {r[1] for r in s.connection().exec_driver_sql(f"PRAGMA table_info({t})").fetchall()}
    @classmethod
    def transfer(cls,product_id,quantity,from_warehouse,to_warehouse,notes="تحويل مخزني",user_id=None):
        q=Decimal(str(quantity))
        if q<=0 or from_warehouse==to_warehouse: raise ValueError("بيانات التحويل غير صحيحة")
        with get_session() as s:
            try:
                PermissionService.ensure_schema(s)
                if user_id is None or not PermissionService.has_in_session(s, user_id, "inventory.transfer"):
                    raise PermissionError("لا توجد صلاحية لتحويل المخزون")
                row=s.execute(text("SELECT quantity,reserved_quantity,average_cost FROM stock_balances WHERE product_id=:p AND warehouse_id=:w"),{"p":product_id,"w":from_warehouse}).fetchone()
                if not row or Decimal(str((row.quantity or 0) - (row.reserved_quantity or 0)))<q: raise ValueError("المخزون المتاح غير كاف")
                s.execute(text("UPDATE stock_balances SET quantity=quantity-:q,last_movement_at=CURRENT_TIMESTAMP WHERE product_id=:p AND warehouse_id=:w"),{"q":float(q),"p":product_id,"w":from_warehouse})
                dest=s.execute(text("SELECT id FROM stock_balances WHERE product_id=:p AND warehouse_id=:w"),{"p":product_id,"w":to_warehouse}).fetchone()
                if dest: s.execute(text("UPDATE stock_balances SET quantity=quantity+:q,last_movement_at=CURRENT_TIMESTAMP WHERE id=:id"),{"q":float(q),"id":dest.id})
                else: s.execute(text("INSERT INTO stock_balances(product_id,warehouse_id,quantity,reserved_quantity,average_cost,last_movement_at) VALUES(:p,:w,:q,0,:c,CURRENT_TIMESTAMP)"),{"p":product_id,"w":to_warehouse,"q":float(q),"c":float(row.average_cost or 0)})
                cols=cls._cols(s,"stock_movements")
                for wh,sign in ((from_warehouse,-1),(to_warehouse,1)):
                    if {"product_id","warehouse_id","quantity"}.issubset(cols):
                        f=["product_id","warehouse_id","quantity"];v=[":p",":w",":q"];d={"p":product_id,"w":wh,"q":float(q*sign)}
                        if "movement_type" in cols:f.append("movement_type");v.append("'TRANSFER'")
                        if "notes" in cols:f.append("notes");v.append(":n");d["n"]=notes
                        if "created_at" in cols:f.append("created_at");v.append("CURRENT_TIMESTAMP")
                        s.execute(text(f"INSERT INTO stock_movements({','.join(f)}) VALUES({','.join(v)})"),d)
                AuditService.log(s,"STOCK_TRANSFER","stock",product_id);s.commit()
            except Exception:s.rollback();raise
    @classmethod
    def adjust(cls,product_id,warehouse_id,new_quantity,reason="تسوية جرد",user_id=None):
        q=Decimal(str(new_quantity))
        if q<0: raise ValueError("الكمية لا يمكن أن تكون سالبة")
        with get_session() as s:
            try:
                PermissionService.ensure_schema(s)
                if user_id is None or not PermissionService.has_in_session(s, user_id, "inventory.adjust"):
                    raise PermissionError("لا توجد صلاحية لتعديل المخزون")
                row=s.execute(text("""
                    SELECT quantity,reserved_quantity,average_cost
                    FROM stock_balances
                    WHERE product_id=:p AND warehouse_id=:w
                    LIMIT 1
                """),{"p":product_id,"w":warehouse_id}).fetchone()
                old=Decimal(str((row.quantity if row else 0) or 0));delta=q-old
                if row:
                    if q < Decimal(str(row.reserved_quantity or 0)):
                        raise ValueError("لا يمكن أن يصبح المخزون أقل من الكمية المحجوزة")
                    s.execute(text("""
                        UPDATE stock_balances
                        SET quantity=:q,last_movement_at=CURRENT_TIMESTAMP
                        WHERE product_id=:p AND warehouse_id=:w
                    """),{"q":float(q),"p":product_id,"w":warehouse_id})
                else:
                    s.execute(text("""
                        INSERT INTO stock_balances(product_id,warehouse_id,quantity,reserved_quantity,average_cost,last_movement_at)
                        VALUES(:p,:w,:q,0,0,CURRENT_TIMESTAMP)
                    """),{"p":product_id,"w":warehouse_id,"q":float(q)})
                cols=cls._cols(s,"stock_movements");f=["product_id","warehouse_id","quantity"];v=[":p",":w",":q"];d={"p":product_id,"w":warehouse_id,"q":float(delta)}
                if "movement_type" in cols:f.append("movement_type");v.append("'ADJUSTMENT'")
                if "notes" in cols:f.append("notes");v.append(":n");d["n"]=reason
                if "created_at" in cols:f.append("created_at");v.append("CURRENT_TIMESTAMP")
                s.execute(text(f"INSERT INTO stock_movements({','.join(f)}) VALUES({','.join(v)})"),d)
                AuditService.log(s,"STOCK_ADJUSTMENT","stock",product_id);s.commit()
            except Exception:s.rollback();raise
