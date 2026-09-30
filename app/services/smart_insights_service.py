from sqlalchemy import text
from app.database.connection import get_session


class SmartInsightsService:
    """محرك معلومات تشغيلي: ملف 360° للمنتج والعميل والمورد مع مؤشرات وتنبيهات."""

    @staticmethod
    def _exists(s, table):
        return bool(s.execute(
            text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:name"),
            {"name": table},
        ).scalar())

    @staticmethod
    def _cols(s, table):
        if not SmartInsightsService._exists(s, table):
            return set()
        return {r[1] for r in s.connection().exec_driver_sql(
            f"PRAGMA table_info({table})"
        ).fetchall()}

    @staticmethod
    def _first(cols, *names):
        for name in names:
            if name in cols:
                return name
        return None

    @classmethod
    def product_360(cls, product_id):
        with get_session() as s:
            p = s.execute(text("SELECT * FROM products WHERE id=:id"), {"id": product_id}).mappings().first()
            if not p:
                return None
            p = dict(p)
            warehouses = []
            if cls._exists(s, "stock") and cls._exists(s, "warehouses"):
                rows = s.execute(text("""
                    SELECT w.id warehouse_id, w.name warehouse_name,
                           COALESCE(st.quantity,0) quantity,
                           COALESCE(st.available_quantity,0) available_quantity,
                           COALESCE(st.average_cost,0) average_cost
                    FROM warehouses w
                    LEFT JOIN stock st ON st.warehouse_id=w.id AND st.product_id=:id
                    WHERE COALESCE(w.is_active,1)=1
                    ORDER BY w.id
                """), {"id": product_id}).mappings().all()
                warehouses = [dict(r) for r in rows]

            sales = []
            if cls._exists(s, "sale_items") and cls._exists(s, "sales"):
                ic = cls._cols(s, "sale_items")
                sc = cls._cols(s, "sales")
                fk = cls._first(ic, "sale_id")
                qty = cls._first(ic, "quantity")
                price = cls._first(ic, "unit_price")
                total = cls._first(ic, "line_total")
                date = cls._first(sc, "created_at", "sale_date", "invoice_date")
                if fk and qty:
                    amount = f"COALESCE(si.{total},0)" if total else (f"si.{qty}*COALESCE(si.{price},0)" if price else f"si.{qty}")
                    date_expr = f"s.{date}" if date else "NULL"
                    rows = s.execute(text(f"""
                        SELECT s.id, s.invoice_number, {date_expr} event_date,
                               si.{qty} quantity, {amount} amount
                        FROM sale_items si JOIN sales s ON s.id=si.{fk}
                        WHERE si.product_id=:id
                        ORDER BY s.id DESC LIMIT 100
                    """), {"id": product_id}).mappings().all()
                    sales = [dict(r) for r in rows]

            purchases = []
            if cls._exists(s, "purchase_invoice_items") and cls._exists(s, "purchase_invoices"):
                ic = cls._cols(s, "purchase_invoice_items")
                pc = cls._cols(s, "purchase_invoices")
                fk = cls._first(ic, "invoice_id", "purchase_invoice_id")
                qty = cls._first(ic, "quantity")
                cost = cls._first(ic, "unit_cost", "cost")
                total = cls._first(ic, "line_total")
                date = cls._first(pc, "invoice_date", "created_at", "purchase_date")
                if fk and qty:
                    amount = f"COALESCE(piix.{total},0)" if total else (f"piix.{qty}*COALESCE(piix.{cost},0)" if cost else f"piix.{qty}")
                    date_expr = f"pi.{date}" if date else "NULL"
                    rows = s.execute(text(f"""
                        SELECT pi.id, pi.invoice_number, {date_expr} event_date,
                               piix.{qty} quantity, {amount} amount
                        FROM purchase_invoice_items piix JOIN purchase_invoices pi ON pi.id=piix.{fk}
                        WHERE piix.product_id=:id
                        ORDER BY pi.id DESC LIMIT 100
                    """), {"id": product_id}).mappings().all()
                    purchases = [dict(r) for r in rows]

            stock_total = sum(float(x.get("quantity") or 0) for x in warehouses)
            available_total = sum(float(x.get("available_quantity") or 0) for x in warehouses)
            sales_qty = sum(float(x.get("quantity") or 0) for x in sales)
            sales_amount = sum(float(x.get("amount") or 0) for x in sales)
            purchase_qty = sum(float(x.get("quantity") or 0) for x in purchases)
            purchase_amount = sum(float(x.get("amount") or 0) for x in purchases)
            cost = float(p.get("cost_price") or 0)
            margin = ((float(p.get("sale_price") or 0) - cost) / float(p.get("sale_price") or 1) * 100) if p.get("sale_price") else 0

            alerts = []
            reorder = float(p.get("reorder_point") or p.get("min_stock") or 0)
            if available_total <= reorder:
                alerts.append(("حرج", "المخزون عند/دون نقطة إعادة الطلب"))
            if sales_qty == 0 and stock_total > 0:
                alerts.append(("تنبيه", "يوجد مخزون بلا مبيعات مسجلة"))
            if cost > float(p.get("sale_price") or 0) and float(p.get("sale_price") or 0) > 0:
                alerts.append(("حرج", "سعر البيع أقل من التكلفة"))

            return {
                "type": "product",
                "title": p.get("name_ar") or p.get("sku") or f"منتج {product_id}",
                "code": p.get("sku") or "",
                "data": p,
                "metrics": [
                    ("المخزون الكلي", stock_total), ("المتاح للبيع", available_total),
                    ("كمية المبيعات", sales_qty), ("قيمة المبيعات", sales_amount),
                    ("كمية المشتريات", purchase_qty), ("قيمة المشتريات", purchase_amount),
                    ("هامش السعر الحالي %", round(margin, 2)),
                ],
                "alerts": alerts,
                "warehouses": warehouses,
                "sales": sales,
                "purchases": purchases,
            }

    @classmethod
    def party_360(cls, party_type, party_id):
        table = "customers" if party_type == "customer" else "suppliers"
        code = "customer_code" if party_type == "customer" else "supplier_code"
        invoice_table = "sales" if party_type == "customer" else "purchase_invoices"
        foreign = "customer_id" if party_type == "customer" else "supplier_id"
        with get_session() as s:
            if not cls._exists(s, table):
                return None
            row = s.execute(text(f"SELECT * FROM {table} WHERE id=:id"), {"id": party_id}).mappings().first()
            if not row:
                return None
            data = dict(row)
            if not cls._exists(s, invoice_table):
                return {"type": party_type, "title": data.get("name") or f"{party_type} {party_id}", "code": data.get(code) or "", "data": data, "metrics": [], "documents": [], "alerts": []}
            cols = cls._cols(s, invoice_table)
            amount = cls._first(cols, "total_amount", "total")
            paid = cls._first(cols, "paid_amount", "paid")
            due = cls._first(cols, "due_amount", "due")
            date = cls._first(cols, "created_at", "invoice_date", "sale_date")
            if not amount:
                amount = "id"
            metrics = s.execute(text(f"""
                SELECT COUNT(*) count,
                       COALESCE(SUM({amount}),0) total,
                       COALESCE(SUM({paid}),0) paid,
                       COALESCE(SUM({due}),0) due
                FROM {invoice_table} WHERE {foreign}=:id
            """), {"id": party_id}).mappings().one()
            select_date = f", {date} event_date" if date else ""
            docs = s.execute(text(f"""
                SELECT id, invoice_number, {amount} total_amount,
                       {paid if paid else '0'} paid_amount,
                       {due if due else '0'} due_amount
                       {select_date}
                FROM {invoice_table}
                WHERE {foreign}=:id
                ORDER BY id DESC LIMIT 100
            """), {"id": party_id}).mappings().all()
            alerts = []
            balance = float(data.get("current_balance") or 0)
            if balance != 0:
                alerts.append(("معلومة", f"الرصيد الحالي: {balance:.2f}"))
            return {
                "type": party_type, "title": data.get("name") or f"{party_type} {party_id}",
                "code": data.get(code) or "", "data": data,
                "metrics": [
                    ("عدد الفواتير", int(metrics["count"] or 0)),
                    ("الإجمالي", float(metrics["total"] or 0)),
                    ("المدفوع", float(metrics["paid"] or 0)),
                    ("المتبقي", float(metrics["due"] or 0)),
                    ("الرصيد الحالي", balance),
                ],
                "documents": [dict(x) for x in docs],
                "alerts": alerts,
            }


    @classmethod
    def document_360(cls, kind, entity_id):
        table = "sales" if kind == "sale" else "purchase_invoices"
        items = "sale_items" if kind == "sale" else "purchase_invoice_items"
        with get_session() as s:
            row = s.execute(text(f"SELECT * FROM {table} WHERE id=:id"), {"id": entity_id}).mappings().first()
            if not row:
                return None
            data = dict(row)
            ic = cls._cols(s, items)
            fk = "sale_id" if kind == "sale" else cls._first(ic, "invoice_id", "purchase_invoice_id")
            history = []
            if fk and cls._exists(s, items):
                rows = s.execute(text(f"""
                    SELECT i.*, p.name_ar, p.sku
                    FROM {items} i LEFT JOIN products p ON p.id=i.product_id
                    WHERE i.{fk}=:id ORDER BY i.id
                """), {"id": entity_id}).mappings().all()
                history = [dict(x) for x in rows]
            title = ("فاتورة بيع " if kind == "sale" else "فاتورة شراء ") + str(data.get("invoice_number") or entity_id)
            return {
                "type": kind, "title": title, "code": data.get("invoice_number") or "",
                "data": data,
                "metrics": [
                    ("عدد البنود", len(history)),
                    ("الإجمالي", float(data.get("total_amount") or 0)),
                    ("المدفوع", float(data.get("paid_amount") or 0)),
                    ("المتبقي", float(data.get("due_amount") or 0)),
                ],
                "alerts": [],
                "documents": history,
            }

    @classmethod
    def simple_360(cls, kind, entity_id):
        table_map = {"account": "accounts", "employee": "employees", "warehouse": "warehouses"}
        table = table_map.get(kind)
        if not table:
            return None
        with get_session() as s:
            if not cls._exists(s, table):
                return None
            row = s.execute(text(f"SELECT * FROM {table} WHERE id=:id"), {"id": entity_id}).mappings().first()
            if not row:
                return None
            data = dict(row)
            title = data.get("name") or data.get("account_name") or data.get("full_name") or data.get("code") or f"{kind} {entity_id}"
            return {"type": kind, "title": title, "code": data.get("code") or data.get("account_code") or "",
                    "data": data, "metrics": [], "alerts": [], "documents": []}

    @classmethod
    def profile(cls, kind, entity_id):
        if kind == "product":
            return cls.product_360(entity_id)
        if kind in {"customer", "supplier"}:
            return cls.party_360(kind, entity_id)
        if kind in {"sale", "purchase"}:
            return cls.document_360(kind, entity_id)
        if kind in {"account", "employee", "warehouse"}:
            return cls.simple_360(kind, entity_id)
        return None
