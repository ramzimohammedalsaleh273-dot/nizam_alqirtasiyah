import json
from datetime import datetime
from sqlalchemy import text
from app.database.connection import get_session
from app.services.audit_service import AuditService
from app.services.document_number_service import DocumentNumberService


class POSHoldService:
    """حفظ واسترجاع فواتير POS المعلقة بشكل دائم داخل قاعدة البيانات."""

    @staticmethod
    def ensure_table(session):
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS pos_held_sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hold_number VARCHAR(100) NOT NULL UNIQUE,
                cashier_id INTEGER NULL,
                customer_id INTEGER NULL,
                warehouse_id INTEGER NOT NULL DEFAULT 1,
                branch_id INTEGER NOT NULL DEFAULT 1,
                payload_json TEXT NOT NULL,
                notes TEXT NULL,
                status VARCHAR(30) NOT NULL DEFAULT 'HELD',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                resumed_at DATETIME NULL,
                resumed_by INTEGER NULL
            )
        """))

    @classmethod
    def hold(cls, items, payment_method="cash", customer_id=None,
             warehouse_id=1, branch_id=1, cashier_id=None, notes=None):
        if not items:
            raise ValueError("لا يمكن تعليق فاتورة فارغة")
        with get_session() as s:
            try:
                cls.ensure_table(s)
                hold_number = DocumentNumberService.next_number(s, "POS_HOLD", "HLD", 6)
                payload = json.dumps({
                    "items": items, "payment_method": payment_method,
                    "customer_id": customer_id
                }, ensure_ascii=False, default=str)
                s.execute(text("""
                    INSERT INTO pos_held_sales
                    (hold_number, cashier_id, customer_id, warehouse_id, branch_id,
                     payload_json, notes, status, created_at)
                    VALUES (:n,:cashier,:customer,:warehouse,:branch,:payload,:notes,'HELD',CURRENT_TIMESTAMP)
                """), {"n": hold_number, "cashier": cashier_id, "customer": customer_id,
                       "warehouse": warehouse_id, "branch": branch_id,
                       "payload": payload, "notes": notes})
                hold_id = int(s.execute(text("SELECT last_insert_rowid()")).scalar())
                AuditService.log(s, "POS_HOLD", "pos_held_sale", hold_id,
                                 username=str(cashier_id) if cashier_id else None)
                s.commit()
                return {"id": hold_id, "hold_number": hold_number}
            except Exception:
                s.rollback()
                raise

    @classmethod
    def list_held(cls, cashier_id=None):
        with get_session() as s:
            cls.ensure_table(s)
            if cashier_id is None:
                rows = s.execute(text("""
                    SELECT * FROM pos_held_sales
                    WHERE status='HELD' ORDER BY id DESC
                """)).fetchall()
            else:
                rows = s.execute(text("""
                    SELECT * FROM pos_held_sales
                    WHERE status='HELD' AND cashier_id=:cashier
                    ORDER BY id DESC
                """), {"cashier": cashier_id}).fetchall()
            return [dict(r._mapping) for r in rows]

    @classmethod
    def resume(cls, hold_id, cashier_id=None):
        with get_session() as s:
            try:
                cls.ensure_table(s)
                row = s.execute(text("""
                    SELECT * FROM pos_held_sales
                    WHERE id=:id AND status='HELD'
                    LIMIT 1
                """), {"id": hold_id}).fetchone()
                if not row:
                    raise ValueError("الفاتورة المعلقة غير موجودة أو تمت معالجتها")
                if cashier_id is not None and row.cashier_id not in (None, cashier_id):
                    raise ValueError("الفاتورة المعلقة تخص كاشيرًا آخر")
                payload = json.loads(row.payload_json)
                s.execute(text("""
                    UPDATE pos_held_sales
                    SET status='RESUMED', resumed_at=CURRENT_TIMESTAMP, resumed_by=:cashier
                    WHERE id=:id AND status='HELD'
                """), {"id": hold_id, "cashier": cashier_id})
                AuditService.log(s, "POS_RESUME", "pos_held_sale", hold_id,
                                 username=str(cashier_id) if cashier_id else None)
                s.commit()
                return {"id": hold_id, "hold_number": row.hold_number, **payload,
                        "warehouse_id": row.warehouse_id, "branch_id": row.branch_id}
            except Exception:
                s.rollback()
                raise

    @classmethod
    def cancel(cls, hold_id, cashier_id=None, reason="إلغاء فاتورة معلقة"):
        with get_session() as s:
            try:
                cls.ensure_table(s)
                row = s.execute(text("""
                    SELECT * FROM pos_held_sales
                    WHERE id=:id AND status='HELD' LIMIT 1
                """), {"id": hold_id}).fetchone()
                if not row:
                    raise ValueError("الفاتورة المعلقة غير موجودة")
                if cashier_id is not None and row.cashier_id not in (None, cashier_id):
                    raise ValueError("لا يحق لهذا الكاشير إلغاء الفاتورة المعلقة")
                s.execute(text("""
                    UPDATE pos_held_sales
                    SET status='CANCELLED', resumed_at=CURRENT_TIMESTAMP, resumed_by=:cashier
                    WHERE id=:id AND status='HELD'
                """), {"id": hold_id, "cashier": cashier_id})
                AuditService.log(s, "POS_HOLD_CANCELLED", "pos_held_sale", hold_id,
                                 username=str(cashier_id) if cashier_id else None)
                s.commit()
                return {"id": hold_id, "status": "CANCELLED"}
            except Exception:
                s.rollback()
                raise
