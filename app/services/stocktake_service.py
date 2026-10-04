from decimal import Decimal
from sqlalchemy import text
from app.database.connection import get_session
from app.services.audit_service import AuditService
from app.services.permission_service import PermissionService

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
    def create(cls, warehouse_id=1, notes=None, user_id=None):
        with get_session() as s:
            cls._ensure(s)
            PermissionService.require_in_session(s, user_id, 'inventory.stocktake')
            r=s.execute(text("""
                INSERT INTO stocktakes(warehouse_id,status,notes)
                VALUES(:w,'DRAFT',:n)
            """),{"w":warehouse_id,"n":notes}).lastrowid
            s.commit()
            return int(r)

    @classmethod
    def add_count(cls, stocktake_id, product_id, counted_quantity, user_id=None):
        q=Decimal(str(counted_quantity))
        if q<0: raise ValueError("الكمية المعدودة لا يمكن أن تكون سالبة")
        with get_session() as s:
            cls._ensure(s)
            PermissionService.require_in_session(s, user_id, 'inventory.stocktake')
            st=s.execute(text("SELECT warehouse_id,status FROM stocktakes WHERE id=:id"),{"id":stocktake_id}).fetchone()
            if not st: raise ValueError("الجرد غير موجود")
            if st.status!="DRAFT": raise ValueError("الجرد مغلق")
            row=s.execute(text("""
                SELECT COALESCE(quantity,0) FROM stock_balances
                WHERE product_id=:p AND warehouse_id=:w
            """),{"p":product_id,"w":st.warehouse_id}).fetchone()
            system=Decimal(str((row[0] if row else 0) or 0))
            diff=q-system
            existing = s.execute(text("""
                SELECT id FROM stocktake_items
                WHERE stocktake_id=:st AND product_id=:p LIMIT 1
            """), {"st": stocktake_id, "p": product_id}).scalar()
            if existing:
                s.execute(text("""
                    UPDATE stocktake_items
                    SET counted_quantity=:cnt, difference=:dif
                    WHERE id=:id
                """), {"id": int(existing), "cnt": float(q), "dif": float(diff)})
            else:
                s.execute(text("""
                    INSERT INTO stocktake_items(stocktake_id,product_id,system_quantity,counted_quantity,difference)
                    VALUES(:st,:p,:sys,:cnt,:dif)
                """), {"st": stocktake_id, "p": product_id, "sys": float(system), "cnt": float(q), "dif": float(diff)})
            s.commit()
            return {"system_quantity":float(system),"counted_quantity":float(q),"difference":float(diff)}

    @classmethod
    def finalize(cls, stocktake_id, reason="إقفال الجرد", user_id=None):
        with get_session() as s:
            cls._ensure(s)
            PermissionService.require_in_session(s, user_id, 'inventory.adjust')
            st=s.execute(text("SELECT warehouse_id,status FROM stocktakes WHERE id=:id"),{"id":stocktake_id}).fetchone()
            if not st: raise ValueError("الجرد غير موجود")
            if st.status!="DRAFT": raise ValueError("الجرد مغلق مسبقًا")
            items=s.execute(text("SELECT product_id,counted_quantity FROM stocktake_items WHERE stocktake_id=:id"),{"id":stocktake_id}).fetchall()
            movement_cols={r[1] for r in s.connection().exec_driver_sql("PRAGMA table_info(stock_movements)").fetchall()}
            for item in items:
                row=s.execute(text("SELECT quantity FROM stock_balances WHERE product_id=:p AND warehouse_id=:w"),{"p":item.product_id,"w":st.warehouse_id}).fetchone()
                old=Decimal(str((row[0] if row else 0) or 0))
                counted=Decimal(str(item.counted_quantity))
                delta=counted-old
                if row:
                    s.execute(text("UPDATE stock_balances SET quantity=:q,last_movement_at=CURRENT_TIMESTAMP WHERE product_id=:p AND warehouse_id=:w"),{"q":float(counted),"p":item.product_id,"w":st.warehouse_id})
                else:
                    s.execute(text("INSERT INTO stock_balances(product_id,warehouse_id,quantity,reserved_quantity,average_cost,last_movement_at) VALUES(:p,:w,:q,0,0,CURRENT_TIMESTAMP)"),{"p":item.product_id,"w":st.warehouse_id,"q":float(counted)})
                fields=["product_id","warehouse_id","quantity"]; vals=[":p",":w",":q"]; params={"p":item.product_id,"w":st.warehouse_id,"q":float(delta)}
                if "movement_type" in movement_cols: fields.append("movement_type"); vals.append("'ADJUSTMENT'")
                if "notes" in movement_cols: fields.append("notes"); vals.append(":n"); params["n"]=reason
                if "reference_type" in movement_cols: fields.append("reference_type"); vals.append("'STOCKTAKE'")
                if "reference_id" in movement_cols: fields.append("reference_id"); vals.append(":sid"); params["sid"]=stocktake_id
                if "created_at" in movement_cols: fields.append("created_at"); vals.append("CURRENT_TIMESTAMP")
                s.execute(text(f"INSERT INTO stock_movements({','.join(fields)}) VALUES({','.join(vals)})"),params)
            s.execute(text("UPDATE stocktakes SET status='COMPLETED',completed_at=CURRENT_TIMESTAMP WHERE id=:id"),{"id":stocktake_id})
            AuditService.log(s,"STOCKTAKE_COMPLETED","stocktake",stocktake_id)
            s.commit()
            return {"id":stocktake_id,"items":len(items),"status":"COMPLETED"}
