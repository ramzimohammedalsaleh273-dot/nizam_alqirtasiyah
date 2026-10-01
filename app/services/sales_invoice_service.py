from sqlalchemy import text
from app.database.connection import get_session


class SalesInvoiceService:
    """خدمات قراءة فاتورة البيع وملفها الكامل دون المساس بالسجل الأصلي."""

    @staticmethod
    def _exists(s, table):
        return bool(s.execute(text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:t"), {"t": table}).scalar())

    @classmethod
    def find_by_number(cls, invoice_number):
        value = str(invoice_number or "").strip()
        if not value:
            return None
        with get_session() as s:
            row = s.execute(text("SELECT * FROM sales WHERE invoice_number=:n LIMIT 1"), {"n": value}).mappings().first()
            return cls._load(s, int(row["id"])) if row else None

    @classmethod
    def get(cls, sale_id):
        with get_session() as s:
            return cls._load(s, int(sale_id))

    @classmethod
    def _load(cls, s, sale_id):
        sale = s.execute(text("SELECT * FROM sales WHERE id=:id"), {"id": sale_id}).mappings().first()
        if not sale:
            return None
        items = s.execute(text("""
            SELECT si.*, p.name_ar, p.sku
            FROM sale_items si LEFT JOIN products p ON p.id=si.product_id
            WHERE si.sale_id=:id ORDER BY si.id
        """), {"id": sale_id}).mappings().all()
        returns = []
        if cls._exists(s, "sale_returns"):
            returns = s.execute(text("""
                SELECT id,return_number,subtotal,tax_amount,total_amount,reason,status,created_at
                FROM sale_returns WHERE sale_id=:id ORDER BY id
            """), {"id": sale_id}).mappings().all()
        return_items = []
        if cls._exists(s, "sale_return_items"):
            return_items = s.execute(text("""
                SELECT sri.*,sr.return_number
                FROM sales_return_items sri JOIN sale_returns sr ON sr.id=sri.return_id
                WHERE sr.sale_id=:id ORDER BY sri.id
            """), {"id": sale_id}).mappings().all()
        payments = []
        if cls._exists(s, "sale_payments"):
            payments = s.execute(text("""
                SELECT payment_method,amount,created_at
                FROM sale_payments WHERE sale_id=:id ORDER BY id
            """), {"id": sale_id}).mappings().all()
        audit = []
        if cls._exists(s, "audit_logs"):
            cols={r[1] for r in s.execute(text("PRAGMA table_info(audit_logs)")).fetchall()}
            date_col="created_at" if "created_at" in cols else ("timestamp" if "timestamp" in cols else None)
            action_col="action" if "action" in cols else ("event_type" if "event_type" in cols else None)
            entity_col="entity_type" if "entity_type" in cols else None
            id_col="entity_id" if "entity_id" in cols else None
            if entity_col and id_col:
                date_sql=date_col or "NULL"; action_sql=action_col or "NULL"
                audit=s.execute(text(
                    f"SELECT {date_sql} event_date,{action_sql} action FROM audit_logs "
                    f"WHERE {entity_col} IN ('sale','sales','invoice') AND {id_col}=:id "
                    "ORDER BY rowid DESC LIMIT 100"
                ), {"id":sale_id}).mappings().all()
        return {
            "sale":dict(sale),"items":[dict(x) for x in items],
            "returns":[dict(x) for x in returns],"return_items":[dict(x) for x in return_items],
            "payments":[dict(x) for x in payments],"audit":[dict(x) for x in audit]
        }

    @staticmethod
    def returned_quantity(data, product_id):
        return sum(float(x.get("quantity") or 0) for x in data.get("return_items", [])
                   if int(x.get("product_id") or 0)==int(product_id))

    @classmethod
    def returnable_items(cls, data):
        result=[]
        for item in data.get("items",[]):
            original=float(item.get("quantity") or 0)
            returned=cls.returned_quantity(data,item.get("product_id"))
            available=max(0.0,original-returned)
            if available>0:
                result.append({
                    "product_id":int(item["product_id"]),
                    "name_ar":item.get("name_ar") or item.get("sku") or str(item["product_id"]),
                    "sku":item.get("sku") or "","original_quantity":original,
                    "returned_quantity":returned,"available_quantity":available,
                    "unit_price":float(item.get("unit_price") or 0)
                })
        return result
