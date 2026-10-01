from sqlalchemy import text
from app.database.connection import get_session


class UniversalSearchService:
    """بحث موحد مع تطبيع عربي للبحث دون تغيير البيانات الأصلية."""
    @staticmethod
    def normalize(value):
        value = str(value or "")
        for a,b in (("أ","ا"),("إ","ا"),("آ","ا"),("ى","ي"),("ة","ه")):
            value=value.replace(a,b)
        return value.strip()
    @staticmethod
    def norm_sql(expr):
        return "REPLACE(REPLACE(REPLACE(REPLACE(REPLACE("+expr+",'أ','ا'),'إ','ا'),'آ','ا'),'ى','ي'),'ة','ه')"

    @staticmethod
    def _exists(s, table):
        return bool(s.execute(
            text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:name"),
            {"name": table},
        ).scalar())

    @staticmethod
    def _cols(s, table):
        if not UniversalSearchService._exists(s, table):
            return set()
        return {r[1] for r in s.connection().exec_driver_sql(
            f"PRAGMA table_info({table})"
        ).fetchall()}

    @classmethod
    def search(cls, term="", limit=80):
        term = cls.normalize(term)
        like = f"%{term}%"
        norm_like = f"%{term}%"
        with get_session() as s:
            out = []

            if cls._exists(s, "products"):
                rows = s.execute(text("""
                    SELECT id, name_ar AS name, sku, 'منتج' AS kind
                    FROM products
                    WHERE is_active=1
                      AND (:term='' OR name_ar LIKE :like OR name_en LIKE :like OR sku LIKE :like
                           OR REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(name_ar,'أ','ا'),'إ','ا'),'آ','ا'),'ى','ي'),'ة','ه') LIKE :norm_like OR EXISTS (SELECT 1 FROM product_barcodes pb
                                      WHERE pb.product_id=products.id AND pb.barcode LIKE :like))
                    ORDER BY id DESC LIMIT :limit
                """), {"term": term, "like": like, "norm_like": norm_like, "limit": limit}).fetchall()
                out += [{"kind": "product", "kind_name": "منتج", "id": r.id,
                         "name": r.name, "code": r.sku or "", "subtitle": r.sku or ""} for r in rows]

            for table, code, kind, label in [
                ("customers", "customer_code", "customer", "عميل"),
                ("suppliers", "supplier_code", "supplier", "مورد"),
            ]:
                if not cls._exists(s, table):
                    continue
                rows = s.execute(text(f"""
                    SELECT id, name, {code} AS code, phone
                    FROM {table}
                    WHERE (:term='' OR name LIKE :like OR {code} LIKE :like OR COALESCE(phone,'') LIKE :like OR REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(name,'أ','ا'),'إ','ا'),'آ','ا'),'ى','ي'),'ة','ه') LIKE :norm_like)
                    ORDER BY id DESC LIMIT :limit
                """), {"term": term, "like": like, "norm_like": norm_like, "limit": limit}).fetchall()
                out += [{"kind": kind, "kind_name": label, "id": r.id,
                         "name": r.name, "code": r.code or "", "subtitle": r.phone or r.code or ""}
                        for r in rows]

            for table, kind, label, names in [
                ("accounts", "account", "حساب محاسبي", ("account_name", "account_code")),
                ("employees", "employee", "موظف", ("full_name", "employee_code")),
                ("warehouses", "warehouse", "مستودع", ("name", "code")),
            ]:
                if not cls._exists(s, table):
                    continue
                cols = cls._cols(s, table)
                name_col = next((x for x in names if x in cols), None)
                code_col = next((x for x in names[1:] if x in cols), None)
                if not name_col:
                    continue
                code_expr = code_col or "''"
                rows = s.execute(text(f"""
                    SELECT id, {name_col} AS name, {code_expr} AS code
                    FROM {table}
                    WHERE (:term='' OR COALESCE({name_col},'') LIKE :like
                           OR COALESCE({code_expr},'') LIKE :like
                           OR REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(COALESCE({name_col},''),'أ','ا'),'إ','ا'),'آ','ا'),'ى','ي'),'ة','ه') LIKE :norm_like)
                    ORDER BY id DESC LIMIT :limit
                """), {"term": term, "like": like, "norm_like": norm_like, "limit": limit}).fetchall()
                out += [{"kind": kind, "kind_name": label, "id": r.id,
                         "name": r.name, "code": r.code or "", "subtitle": r.code or ""}
                        for r in rows]

            if cls._exists(s, "sales"):
                rows = s.execute(text("""
                    SELECT id, invoice_number AS code, total_amount, created_at
                    FROM sales
                    WHERE :term='' OR invoice_number LIKE :like
                    ORDER BY id DESC LIMIT :limit
                """), {"term": term, "like": like, "limit": limit}).fetchall()
                out += [{"kind": "sale", "kind_name": "فاتورة بيع", "id": r.id,
                         "name": f"فاتورة بيع {r.code}", "code": r.code or "",
                         "subtitle": f"الإجمالي: {float(r.total_amount or 0):.2f}"} for r in rows]

            if cls._exists(s, "purchase_invoices"):
                rows = s.execute(text("""
                    SELECT id, invoice_number AS code, total_amount, invoice_date
                    FROM purchase_invoices
                    WHERE :term='' OR invoice_number LIKE :like
                    ORDER BY id DESC LIMIT :limit
                """), {"term": term, "like": like, "limit": limit}).fetchall()
                out += [{"kind": "purchase", "kind_name": "فاتورة شراء", "id": r.id,
                         "name": f"فاتورة شراء {r.code}", "code": r.code or "",
                         "subtitle": f"الإجمالي: {float(r.total_amount or 0):.2f}"} for r in rows]

            # مستندات الخزينة والمستندات العامة ضمن البحث الشامل.
            for table, kind, label, code_col, name_col in [
                ("cash_receipts", "receipt", "سند قبض", "receipt_number", "notes"),
                ("cash_payments", "payment", "سند صرف", "payment_number", "notes"),
                ("documents", "document", "مستند", "document_no", "title"),
            ]:
                if not cls._exists(s, table):
                    continue
                cols = cls._cols(s, table)
                if code_col not in cols:
                    continue
                name_expr = name_col if name_col in cols else "''"
                rows = s.execute(text(f"""
                    SELECT id, {code_col} AS code, COALESCE({name_expr},'') AS name
                    FROM {table}
                    WHERE :term='' OR CAST({code_col} AS TEXT) LIKE :like
                       OR COALESCE({name_expr},'') LIKE :like
                       OR {cls.norm_sql("COALESCE("+name_expr+",'')")} LIKE :norm_like
                    ORDER BY id DESC LIMIT :limit
                """), {"term": term, "like": like, "norm_like": norm_like, "limit": limit}).fetchall()
                out += [{"kind": kind, "kind_name": label, "id": r.id,
                         "name": r.name or f"{label} {r.code}", "code": r.code or "",
                         "subtitle": r.name or ""} for r in rows]

            return out[:limit]

    @classmethod
    def product_profile(cls, product_id):
        with get_session() as s:
            product = s.execute(text("SELECT * FROM products WHERE id=:id"), {"id": product_id}).fetchone()
            if not product:
                return None
            p = dict(product._mapping)

            stock = s.execute(text("""
                SELECT COALESCE(SUM(quantity),0), COALESCE(SUM(available_quantity),0)
                FROM stock WHERE product_id=:id
            """), {"id": product_id}).fetchone() if cls._exists(s, "stock") else (0, 0)

            sales = {"count": 0, "quantity": 0, "amount": 0}
            if cls._exists(s, "sale_items") and cls._exists(s, "sales"):
                ic = cls._cols(s, "sale_items")
                qty = "quantity" if "quantity" in ic else "0"
                amount = "line_total" if "line_total" in ic else f"({qty}*COALESCE(unit_price,0))"
                sales = dict(s.execute(text(f"""
                    SELECT COUNT(DISTINCT si.sale_id) AS count,
                           COALESCE(SUM(si.{qty}),0) AS quantity,
                           COALESCE(SUM({amount}),0) AS amount
                    FROM sale_items si JOIN sales x ON x.id=si.sale_id
                    WHERE si.product_id=:id
                """), {"id": product_id}).mappings().one())

            purchases = {"count": 0, "quantity": 0, "amount": 0}
            if cls._exists(s, "purchase_invoice_items") and cls._exists(s, "purchase_invoices"):
                ic = cls._cols(s, "purchase_invoice_items")
                fk = "invoice_id" if "invoice_id" in ic else "purchase_invoice_id"
                qty = "quantity" if "quantity" in ic else "0"
                amount = "line_total" if "line_total" in ic else f"({qty}*COALESCE(unit_cost,0))"
                purchases = dict(s.execute(text(f"""
                    SELECT COUNT(DISTINCT pi.id) AS count,
                           COALESCE(SUM(pii.{qty}),0) AS quantity,
                           COALESCE(SUM({amount}),0) AS amount
                    FROM purchase_invoice_items pii
                    JOIN purchase_invoices pi ON pi.id=pii.{fk}
                    WHERE pii.product_id=:id
                """), {"product_id": product_id}).mappings().one())

            return {
                "type": "product", "title": p.get("name_ar") or p.get("sku") or f"منتج {product_id}",
                "code": p.get("sku") or "", "data": p,
                "summary": [
                    ("المخزون", float(stock[0] or 0)),
                    ("المتاح", float(stock[1] or 0)),
                    ("عدد فواتير البيع", int(sales["count"] or 0)),
                    ("كمية المبيعات", float(sales["quantity"] or 0)),
                    ("قيمة المبيعات", float(sales["amount"] or 0)),
                    ("عدد فواتير الشراء", int(purchases["count"] or 0)),
                    ("كمية المشتريات", float(purchases["quantity"] or 0)),
                    ("قيمة المشتريات", float(purchases["amount"] or 0)),
                ],
            }

    @classmethod
    def party_profile(cls, party_type, party_id):
        table = "customers" if party_type == "customer" else "suppliers"
        code = "customer_code" if table == "customers" else "supplier_code"
        with get_session() as s:
            row = s.execute(text(f"SELECT * FROM {table} WHERE id=:id"), {"id": party_id}).fetchone()
            if not row:
                return None
            data = dict(row._mapping)
            if table == "customers":
                agg = s.execute(text("""
                    SELECT COUNT(*) count, COALESCE(SUM(total_amount),0) total,
                           COALESCE(SUM(paid_amount),0) paid, COALESCE(SUM(due_amount),0) due
                    FROM sales WHERE customer_id=:id
                """), {"id": party_id}).one()
                title = data.get("name") or f"عميل {party_id}"
            else:
                agg = s.execute(text("""
                    SELECT COUNT(*) count, COALESCE(SUM(total_amount),0) total,
                           COALESCE(SUM(paid_amount),0) paid, COALESCE(SUM(due_amount),0) due
                    FROM purchase_invoices WHERE supplier_id=:id
                """), {"id": party_id}).one()
                title = data.get("name") or f"مورد {party_id}"
            return {
                "type": party_type, "title": title, "code": data.get(code) or "",
                "data": data,
                "summary": [
                    ("عدد العمليات", int(agg.count or 0)),
                    ("إجمالي المشتريات/المبيعات", float(agg.total or 0)),
                    ("إجمالي المدفوع", float(agg.paid or 0)),
                    ("إجمالي المتبقي", float(agg.due or 0)),
                    ("الرصيد الحالي", float(data.get("current_balance") or 0)),
                ],
            }

    @classmethod
    def document_profile(cls, kind, entity_id):
        table = "sales" if kind == "sale" else "purchase_invoices"
        item_table = "sale_items" if kind == "sale" else "purchase_invoice_items"
        with get_session() as s:
            row = s.execute(text(f"SELECT * FROM {table} WHERE id=:id"), {"id": entity_id}).fetchone()
            if not row:
                return None
            data = dict(row._mapping)
            ic = cls._cols(s, item_table)
            fk = "sale_id" if kind == "sale" else ("invoice_id" if "invoice_id" in ic else "purchase_invoice_id")
            items = []
            if fk in ic:
                rows = s.execute(text(f"SELECT i.*, p.name_ar, p.sku FROM {item_table} i LEFT JOIN products p ON p.id=i.product_id WHERE i.{fk}=:id ORDER BY i.id"), {"id": entity_id}).fetchall()
                items = [dict(x._mapping) for x in rows]
            data["_بنود_المستند"] = items
            title = ("فاتورة بيع " if kind == "sale" else "فاتورة شراء ") + str(data.get("invoice_number") or entity_id)
            return {"type": kind, "title": title, "code": data.get("invoice_number") or "", "data": data,
                    "summary": [("عدد البنود", len(items)), ("الإجمالي", float(data.get("total_amount") or 0)),
                                 ("المدفوع", float(data.get("paid_amount") or 0)),
                                 ("المتبقي", float(data.get("due_amount") or 0)), ("الحالة", data.get("status") or "")] }

    @classmethod
    def profile(cls, kind, entity_id):
        if kind == "product":
            return cls.product_profile(entity_id)
        if kind in {"customer", "supplier"}:
            return cls.party_profile(kind, entity_id)
        if kind in {"sale", "purchase"}:
            return cls.document_profile(kind, entity_id)
        return None
