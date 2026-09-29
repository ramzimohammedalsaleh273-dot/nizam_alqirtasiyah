from decimal import Decimal
from sqlalchemy import text
from app.database.connection import get_session
from app.services.audit_service import AuditService
from app.services.document_number_service import DocumentNumberService
from app.services.purchase_service import PurchaseService
from app.services.permission_service import PermissionService


class PurchaseWorkflowService:
    """دورة شراء حقيقية محفوظة: طلب -> اعتماد -> أمر شراء -> استلام/فاتورة."""

    @staticmethod
    def ensure_schema(s):
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS purchase_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_number VARCHAR(100) UNIQUE NOT NULL,
                requester_id INTEGER NULL,
                branch_id INTEGER NOT NULL DEFAULT 1,
                warehouse_id INTEGER NOT NULL DEFAULT 1,
                status VARCHAR(30) NOT NULL DEFAULT 'DRAFT',
                notes TEXT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                approved_at DATETIME NULL,
                approved_by INTEGER NULL
            )
        """))
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS purchase_request_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity NUMERIC NOT NULL,
                notes TEXT NULL
            )
        """))
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS purchase_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_number VARCHAR(100) UNIQUE NOT NULL,
                request_id INTEGER NULL,
                supplier_id INTEGER NOT NULL,
                branch_id INTEGER NOT NULL DEFAULT 1,
                warehouse_id INTEGER NOT NULL DEFAULT 1,
                status VARCHAR(30) NOT NULL DEFAULT 'DRAFT',
                notes TEXT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                approved_at DATETIME NULL
            )
        """))
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS purchase_order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity NUMERIC NOT NULL,
                unit_cost NUMERIC NOT NULL DEFAULT 0
            )
        """))

    @classmethod
    def create_request(cls, items, requester_id=None, branch_id=1, warehouse_id=1, notes=None):
        if not items:
            raise ValueError("طلب الشراء فارغ")
        with get_session() as s:
            try:
                cls.ensure_schema(s)
                PermissionService.ensure_schema(s)
                n = DocumentNumberService.next_number(s, "PURCHASE_REQUEST", "PRQ", 6)
                s.execute(text("""
                    INSERT INTO purchase_requests
                    (request_number,requester_id,branch_id,warehouse_id,status,notes)
                    VALUES (:n,:u,:b,:w,'SUBMITTED',:notes)
                """), {"n":n,"u":requester_id,"b":branch_id,"w":warehouse_id,"notes":notes})
                rid=int(s.execute(text("SELECT last_insert_rowid()")).scalar())
                for x in items:
                    q=Decimal(str(x["quantity"]))
                    if q<=0: raise ValueError("كمية الطلب يجب أن تكون أكبر من صفر")
                    s.execute(text("""
                        INSERT INTO purchase_request_items(request_id,product_id,quantity,notes)
                        VALUES(:r,:p,:q,:n)
                    """), {"r":rid,"p":int(x["product_id"]),"q":float(q),"n":x.get("notes")})
                AuditService.log(s,"PURCHASE_REQUEST_CREATED","purchase_request",rid)
                s.commit()
                return {"id":rid,"request_number":n,"status":"SUBMITTED"}
            except Exception:
                s.rollback(); raise

    @classmethod
    def approve_request(cls, request_id, approved_by):
        with get_session() as s:
            try:
                cls.ensure_schema(s)
                PermissionService.ensure_schema(s)
                if approved_by is None:
                    raise PermissionError("يجب تحديد المستخدم المعتمد")
                if not PermissionService.has_in_session(s, int(approved_by), "purchase.request.approve"):
                    raise PermissionError("المستخدم لا يملك صلاحية اعتماد طلبات الشراء")
                row=s.execute(text("SELECT * FROM purchase_requests WHERE id=:id"),{"id":request_id}).fetchone()
                if not row: raise ValueError("طلب الشراء غير موجود")
                if row.status!="SUBMITTED": raise ValueError("الطلب ليس في حالة انتظار الاعتماد")
                s.execute(text("""
                    UPDATE purchase_requests SET status='APPROVED',
                    approved_at=CURRENT_TIMESTAMP,approved_by=:u WHERE id=:id
                """),{"u":approved_by,"id":request_id})
                AuditService.log(s,"PURCHASE_REQUEST_APPROVED","purchase_request",request_id,username=str(approved_by))
                s.commit()
                return {"id":request_id,"status":"APPROVED"}
            except Exception:
                s.rollback(); raise

    @classmethod
    def create_purchase_order(cls, request_id, supplier_id, items, notes=None):
        if not items: raise ValueError("أمر الشراء فارغ")
        with get_session() as s:
            try:
                cls.ensure_schema(s)
                req=s.execute(text("SELECT * FROM purchase_requests WHERE id=:id"),{"id":request_id}).fetchone()
                if not req or req.status!="APPROVED": raise ValueError("يجب اعتماد طلب الشراء أولاً")
                n=DocumentNumberService.next_number(s,"PURCHASE_ORDER","PO",6)
                s.execute(text("""
                    INSERT INTO purchase_orders
                    (order_number,request_id,supplier_id,branch_id,warehouse_id,status,notes)
                    VALUES(:n,:r,:supplier,:b,:w,'APPROVED',:notes)
                """),{"n":n,"r":request_id,"supplier":supplier_id,"b":req.branch_id,"w":req.warehouse_id,"notes":notes})
                oid=int(s.execute(text("SELECT last_insert_rowid()")).scalar())
                for x in items:
                    q=Decimal(str(x["quantity"])); c=Decimal(str(x["unit_cost"]))
                    if q<=0 or c<0: raise ValueError("كمية أو تكلفة أمر الشراء غير صحيحة")
                    s.execute(text("""
                        INSERT INTO purchase_order_items(order_id,product_id,quantity,unit_cost)
                        VALUES(:o,:p,:q,:c)
                    """),{"o":oid,"p":int(x["product_id"]),"q":float(q),"c":float(c)})
                s.execute(text("UPDATE purchase_requests SET status='ORDERED' WHERE id=:id"),{"id":request_id})
                AuditService.log(s,"PURCHASE_ORDER_CREATED","purchase_order",oid)
                s.commit()
                return {"id":oid,"order_number":n,"status":"APPROVED"}
            except Exception:
                s.rollback(); raise

    @classmethod
    def receive_order(cls, order_id, paid_amount=0, tax_amount=0, payment_method="cash", notes=None):
        """استلام أمر الشراء وفوترته داخل معاملة واحدة."""
        with get_session() as s:
            try:
                cls.ensure_schema(s)
                order=s.execute(
                    text("SELECT * FROM purchase_orders WHERE id=:id"),
                    {"id":order_id},
                ).fetchone()
                if not order:
                    raise ValueError("أمر الشراء غير موجود")
                if order.status=="RECEIVED":
                    raise ValueError("أمر الشراء مستلم مسبقاً")
                if order.status not in {"APPROVED","PARTIAL"}:
                    raise ValueError("أمر الشراء غير جاهز للاستلام")
                rows=s.execute(
                    text("SELECT product_id,quantity,unit_cost FROM purchase_order_items WHERE order_id=:id ORDER BY id"),
                    {"id":order_id},
                ).fetchall()
                if not rows:
                    raise ValueError("أمر الشراء لا يحتوي أصنافاً")

                result=PurchaseService.create_invoice(
                    supplier_id=int(order.supplier_id),
                    items=[{"product_id":int(r.product_id),"quantity":float(r.quantity),"unit_cost":float(r.unit_cost)} for r in rows],
                    warehouse_id=int(order.warehouse_id),
                    branch_id=int(order.branch_id),
                    paid_amount=paid_amount,
                    notes=notes or f"استلام أمر شراء {order.order_number}",
                    payment_method=payment_method,
                    tax_amount=tax_amount,
                    session=s,
                )
                s.execute(
                    text("UPDATE purchase_orders SET status='RECEIVED' WHERE id=:id AND status<>'RECEIVED'"),
                    {"id":order_id},
                )
                if order.request_id is not None:
                    s.execute(
                        text("UPDATE purchase_requests SET status='RECEIVED' WHERE id=:id"),
                        {"id":int(order.request_id)},
                    )
                AuditService.log(s,"PURCHASE_ORDER_RECEIVED","purchase_order",order_id)
                s.commit()
                return {"order_id":order_id,"purchase_invoice":result}
            except Exception:
                s.rollback()
                raise
