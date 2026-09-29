
from __future__ import annotations

from pathlib import Path
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import sqlite3
import json
import uuid


class ERPError(Exception):
    pass


class ERP:
    """
    محرك التشغيل الأساسي لنظام القرطاسية.
    يعمل فوق قاعدة البيانات الحالية دون حذف الجداول الموجودة.
    """

    def __init__(self, db_path):
        self.db_path = str(db_path)

    def connect(self):
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA synchronous=NORMAL")
        return con

    def _columns(self, con, table):
        rows = con.execute(f'PRAGMA table_info("{table}")').fetchall()
        return {r["name"] for r in rows}

    def _exists(self, con, table):
        return bool(con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table,)
        ).fetchone())

    def _q(self, value):
        return Decimal(str(value)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    def _next_number(self, con, prefix, table, column):
        year = datetime.now().strftime("%Y")
        like = f"{prefix}-{year}-%"
        row = con.execute(
            f'SELECT MAX("{column}") AS n FROM "{table}" WHERE "{column}" LIKE ?',
            (like,)
        ).fetchone()
        last = row["n"] if row and row["n"] else None
        seq = 1
        if last:
            try:
                seq = int(str(last).split("-")[-1]) + 1
            except Exception:
                seq = 1
        return f"{prefix}-{year}-{seq:06d}"

    def _insert_dynamic(self, con, table, data):
        cols = self._columns(con, table)
        data = {k: v for k, v in data.items() if k in cols}
        if not data:
            raise ERPError(f"لا توجد أعمدة قابلة للإدخال في {table}")
        names = list(data)
        marks = ",".join("?" for _ in names)
        sql = f'INSERT INTO "{table}" ({",".join(chr(34)+x+chr(34) for x in names)}) VALUES ({marks})'
        cur = con.execute(sql, [data[x] for x in names])
        return cur.lastrowid

    def _product(self, con, product_id):
        row = con.execute(
            "SELECT * FROM products WHERE id=?", (product_id,)
        ).fetchone()
        if not row:
            raise ERPError(f"المنتج غير موجود: {product_id}")
        return row

    def _stock(self, con, product_id, warehouse_id):
        if not self._exists(con, "stock_balances"):
            raise ERPError("جدول stock_balances غير موجود")

        row = con.execute(
            """SELECT * FROM stock_balances
               WHERE product_id=? AND warehouse_id=?""",
            (product_id, warehouse_id)
        ).fetchone()

        if row:
            return row

        self._insert_dynamic(con, "stock_balances", {
            "product_id": product_id,
            "warehouse_id": warehouse_id,
            "quantity": 0,
            "reserved_quantity": 0,
            "average_cost": 0,
            "last_movement_at": datetime.now().isoformat()
        })

        return con.execute(
            """SELECT * FROM stock_balances
               WHERE product_id=? AND warehouse_id=?""",
            (product_id, warehouse_id)
        ).fetchone()

    def _change_stock(
        self, con, product_id, warehouse_id, quantity,
        movement_type, unit_cost=0, reference_type=None,
        reference_id=None, notes=None
    ):
        product = self._product(con, product_id)
        old = self._stock(con, product_id, warehouse_id)

        old_qty = self._q(old["quantity"] or 0)
        qty = self._q(quantity)
        new_qty = old_qty + qty

        if new_qty < 0:
            raise ERPError(
                f"المخزون غير كافٍ للمنتج {product['name_ar']} "
                f"(المتاح {old_qty}, المطلوب {abs(qty)})"
            )

        old_cost = self._q(old["average_cost"] or 0)
        incoming_cost = self._q(unit_cost or product["cost_price"] or 0)

        if qty > 0:
            total_old = old_qty * old_cost
            total_new = qty * incoming_cost
            avg = (total_old + total_new) / new_qty if new_qty else incoming_cost
        else:
            avg = old_cost

        con.execute(
            """UPDATE stock_balances
               SET quantity=?, average_cost=?, last_movement_at=?
               WHERE product_id=? AND warehouse_id=?""",
            (
                float(new_qty),
                float(avg),
                datetime.now().isoformat(),
                product_id,
                warehouse_id
            )
        )

        self._insert_dynamic(con, "stock_movements", {
            "product_id": product_id,
            "warehouse_id": warehouse_id,
            "movement_type": movement_type,
            "quantity": float(qty),
            "unit_cost": float(incoming_cost),
            "reference_type": reference_type,
            "reference_id": reference_id,
            "notes": notes,
            "created_at": datetime.now().isoformat()
        })

        return float(new_qty), float(avg)

    def _account(self, con, code):
        row = con.execute(
            "SELECT * FROM accounts WHERE account_code=? AND is_active=1",
            (code,)
        ).fetchone()
        if not row:
            raise ERPError(f"الحساب المحاسبي غير موجود: {code}")
        return row

    def _journal(self, con, description, lines, reference_type=None, reference_id=None):
        if not self._exists(con, "journal_entries"):
            return None

        je_cols = self._columns(con, "journal_entries")

        number = None
        for candidate in ("entry_number", "journal_number", "number"):
            if candidate in je_cols:
                number = self._next_number(
                    con, "JE", "journal_entries", candidate
                )
                break

        total_debit = sum(self._q(x["debit"]) for x in lines)
        total_credit = sum(self._q(x["credit"]) for x in lines)

        if total_debit != total_credit:
            raise ERPError(
                f"القيد غير متوازن: مدين={total_debit} دائن={total_credit}"
            )

        data = {
            "entry_number": number,
            "journal_number": number,
            "number": number,
            "description": description,
            "reference_type": reference_type,
            "reference_id": reference_id,
            "entry_date": datetime.now().strftime("%Y-%m-%d"),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "status": "POSTED",
            "created_at": datetime.now().isoformat()
        }

        je_id = self._insert_dynamic(con, "journal_entries", data)

        if not self._exists(con, "journal_entry_lines"):
            return je_id

        line_cols = self._columns(con, "journal_entry_lines")

        for line in lines:
            account = self._account(con, line["account_code"])
            self._insert_dynamic(con, "journal_entry_lines", {
                "journal_entry_id": je_id,
                "entry_id": je_id,
                "account_id": account["id"],
                "account_code": account["account_code"],
                "debit": float(self._q(line["debit"])),
                "credit": float(self._q(line["credit"])),
                "description": line.get("description", description),
                "created_at": datetime.now().isoformat()
            })

        return je_id

    def create_product(
        self, sku, name_ar, category_id=1, unit_id=1,
        cost_price=0, sale_price=0, min_stock=0, barcode=None
    ):
        with self.connect() as con:
            if sku and con.execute(
                "SELECT 1 FROM products WHERE sku=? LIMIT 1",
                (sku,)
            ).fetchone():
                raise ERPError(f"SKU موجود مسبقاً: {sku}")

            barcode = str(barcode or "").strip() or None

            if barcode and con.execute(
                "SELECT 1 FROM product_barcodes WHERE barcode=? LIMIT 1",
                (barcode,)
            ).fetchone():
                raise ERPError(f"الباركود موجود مسبقاً: {barcode}")

            # إنشاء المنتج
            self._insert_dynamic(con, "products", {
                "sku": sku,
                "name_ar": name_ar,
                "category_id": category_id,
                "unit_id": unit_id,
                "cost_price": float(cost_price),
                "sale_price": float(sale_price),
                "wholesale_price": float(sale_price),
                "school_price": float(sale_price),
                "corporate_price": float(sale_price),
                "min_price": float(sale_price),
                "reorder_point": float(min_stock),
                "min_stock": float(min_stock),
                "max_stock": float(min_stock * 10 if min_stock else 0),
                "is_active": 1,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            })

            # الحصول على رقم المنتج مباشرة من قاعدة البيانات
            row = con.execute(
                "SELECT id FROM products WHERE sku=? ORDER BY id DESC LIMIT 1",
                (sku,)
            ).fetchone()

            if not row:
                raise ERPError("تمت محاولة إنشاء المنتج ولكن لم يتم العثور على رقمه")

            product_id = int(row[0])

            # تسجيل الباركود في جدوله الصحيح
            if barcode:
                con.execute(
                    """
                    INSERT INTO product_barcodes
                    (product_id, barcode, is_primary)
                    VALUES (?, ?, 1)
                    """,
                    (product_id, barcode)
                )

            return product_id

    def create_purchase(self, supplier_id, items):
        if not items:
            raise ERPError("لا توجد أصناف في أمر الشراء")
        with self.connect() as con:
            total=0
            rows=[]
            for item in items:
                product=self._product(con,item["product_id"])
                qty=float(item["quantity"])
                cost=float(item["unit_cost"])
                if qty<=0 or cost<0:
                    raise ERPError("كمية أو تكلفة غير صحيحة")
                line=qty*cost
                total+=line
                rows.append((product,qty,cost,line))
            number=self._next_number(con,"PO","purchase_orders","order_number")
            branch = con.execute("SELECT id FROM branches ORDER BY id LIMIT 1").fetchone()
            warehouse = con.execute("SELECT id FROM warehouses ORDER BY id LIMIT 1").fetchone()

            data={
                "order_number":number,
                "supplier_id":supplier_id,
                "status":"DRAFT",
                "total_amount":total,
            }

            if branch and "branch_id" in self._columns(con, "purchase_orders"):
                data["branch_id"] = branch[0]

            if warehouse and "warehouse_id" in self._columns(con, "purchase_orders"):
                data["warehouse_id"] = warehouse[0]
            oid=self._insert_dynamic(con,"purchase_orders",data)
            for product,qty,cost,line in rows:
                item_data={
                    "purchase_order_id":oid,
                    "order_id":oid,
                    "product_id":product["id"],
                    "quantity":qty,
                    "unit_cost":cost,
                    "total":line,
                }
                self._insert_dynamic(con,"purchase_order_items",item_data)
            return {"purchase_id":oid,"total":total,"status":"CREATED"}

    def receive_purchase(
        self, supplier_id, warehouse_id, items,
        branch_id=1, tax_rate=15
    ):
        """
        items = [{"product_id": 1, "quantity": 10, "unit_cost": 5}]
        """
        with self.connect() as con:
            now = datetime.now().isoformat()
            order_no = self._next_number(
                con, "PO", "purchase_orders", "order_number"
            )

            subtotal = self._q(0)

            for item in items:
                subtotal += self._q(item["quantity"]) * self._q(item["unit_cost"])

            tax = self._q(subtotal * self._q(tax_rate) / 100)
            total = subtotal + tax

            po_id = self._insert_dynamic(con, "purchase_orders", {
                "order_number": order_no,
                "branch_id": branch_id,
                "supplier_id": supplier_id,
                "status": "RECEIVED",
                "subtotal": float(subtotal),
                "discount_amount": 0,
                "tax_amount": float(tax),
                "total_amount": float(total),
                "notes": "إدخال شراء تشغيلي",
                "created_at": now
            })

            for item in items:
                qty = self._q(item["quantity"])
                cost = self._q(item["unit_cost"])
                line = qty * cost

                self._insert_dynamic(con, "purchase_order_items", {
                    "order_id": po_id,
                    "product_id": item["product_id"],
                    "quantity": float(qty),
                    "unit_cost": float(cost),
                    "tax_amount": 0,
                    "line_total": float(line)
                })

                self._change_stock(
                    con,
                    item["product_id"],
                    warehouse_id,
                    qty,
                    "PURCHASE",
                    cost,
                    "PURCHASE_ORDER",
                    po_id,
                    "استلام شراء"
                )

            invoice_no = self._next_number(
                con, "PINV", "purchase_invoices", "invoice_number"
            )

            invoice_id = self._insert_dynamic(con, "purchase_invoices", {
                "invoice_number": invoice_no,
                "supplier_id": supplier_id,
                "purchase_order_id": po_id,
                "subtotal": float(subtotal),
                "tax_amount": float(tax),
                "total_amount": float(total),
                "paid_amount": 0,
                "due_amount": float(total),
                "status": "POSTED",
                "invoice_date": now[:10],
                "due_date": now[:10]
            })

            for item in items:
                qty = self._q(item["quantity"])
                cost = self._q(item["unit_cost"])
                self._insert_dynamic(con, "purchase_invoice_items", {
                    "invoice_id": invoice_id,
                    "product_id": item["product_id"],
                    "quantity": float(qty),
                    "unit_cost": float(cost),
                    "tax_amount": 0,
                    "line_total": float(qty * cost)
                })

            # الربط المحاسبي الصحيح للشراء:
            # المخزون = صافي قيمة البضاعة
            # ضريبة المدخلات = أصل ضريبي
            # الموردون = إجمالي الفاتورة
            self._journal(
                con,
                f"فاتورة شراء {invoice_no}",
                [
                    {
                        "account_code": "1400",
                        "debit": subtotal,
                        "credit": 0,
                        "description": "إثبات صافي المخزون"
                    },
                    {
                        "account_code": "1410",
                        "debit": tax,
                        "credit": 0,
                        "description": "إثبات ضريبة القيمة المضافة - مدخلات"
                    },
                    {
                        "account_code": "2100",
                        "debit": 0,
                        "credit": total,
                        "description": "إثبات إجمالي ذمة المورد"
                    }
                ],
                "PURCHASE",
                invoice_id
            )

            return {
                "purchase_order_id": po_id,
                "purchase_invoice_id": invoice_id,
                "number": invoice_no,
                "subtotal": float(subtotal),
                "tax": float(tax),
                "total": float(total)
            }

    def create_sale(
        self, warehouse_id, items, customer_id=None,
        branch_id=1, cashier_id=1, payments=None,
        tax_rate=15
    ):
        """
        items = [{"product_id": 1, "quantity": 2, "unit_price": 10}]
        payments = [{"payment_method": "CASH", "amount": 23}]
        """
        with self.connect() as con:
            now = datetime.now().isoformat()
            invoice_no = self._next_number(
                con, "INV", "sales", "invoice_number"
            )

            subtotal = self._q(0)
            cost_total = self._q(0)

            prepared = []

            for item in items:
                product = self._product(con, item["product_id"])
                qty = self._q(item["quantity"])
                price = self._q(
                    item.get("unit_price", product["sale_price"])
                )
                discount = self._q(item.get("discount_amount", 0))

                if qty <= 0:
                    raise ERPError("كمية البيع يجب أن تكون أكبر من صفر")

                line_total = (qty * price) - discount

                stock = self._stock(
                    con, item["product_id"], warehouse_id
                )

                if self._q(stock["quantity"] or 0) < qty:
                    raise ERPError(
                        f"المخزون غير كافٍ للمنتج: {product['name_ar']}"
                    )

                cost = self._q(
                    stock["average_cost"] or product["cost_price"] or 0
                )

                subtotal += line_total
                cost_total += qty * cost

                prepared.append({
                    "product_id": item["product_id"],
                    "quantity": qty,
                    "unit_price": price,
                    "discount": discount,
                    "line_total": line_total,
                    "cost": cost
                })

            tax = self._q(subtotal * self._q(tax_rate) / 100)
            total = subtotal + tax

            paid = self._q(
                sum(self._q(x["amount"]) for x in (payments or []))
            )
            due = total - paid

            if due < 0:
                raise ERPError("المبلغ المدفوع أكبر من إجمالي الفاتورة")

            sale_id = self._insert_dynamic(con, "sales", {
                "invoice_number": invoice_no,
                "branch_id": branch_id,
                "warehouse_id": warehouse_id,
                "customer_id": customer_id,
                "cashier_id": cashier_id,
                "status": "POSTED",
                "subtotal": float(subtotal),
                "discount_amount": float(sum(x["discount"] for x in prepared)),
                "tax_amount": float(tax),
                "total_amount": float(total),
                "paid_amount": float(paid),
                "due_amount": float(due),
                "notes": "فاتورة بيع تشغيلية",
                "created_at": now
            })

            for x in prepared:
                line_tax = self._q(
                    x["line_total"] * self._q(tax_rate) / 100
                )

                self._insert_dynamic(con, "sale_items", {
                    "sale_id": sale_id,
                    "product_id": x["product_id"],
                    "quantity": float(x["quantity"]),
                    "unit_price": float(x["unit_price"]),
                    "discount_amount": float(x["discount"]),
                    "tax_amount": float(line_tax),
                    "line_total": float(x["line_total"] + line_tax)
                })

                self._change_stock(
                    con,
                    x["product_id"],
                    warehouse_id,
                    -x["quantity"],
                    "SALE",
                    x["cost"],
                    "SALE",
                    sale_id,
                    "صرف بيع"
                )

            for payment in (payments or []):
                self._insert_dynamic(con, "sale_payments", {
                    "sale_id": sale_id,
                    "payment_method": payment["payment_method"],
                    "amount": float(self._q(payment["amount"])),
                    "reference_number": payment.get("reference_number"),
                    "notes": payment.get("notes")
                })

                if self._exists(con, "cash_transactions"):
                    self._insert_dynamic(con, "cash_transactions", {
                        "transaction_type": "SALE",
                        "amount": float(self._q(payment["amount"])),
                        "reference_type": "SALE",
                        "reference_id": sale_id,
                        "description": f"تحصيل فاتورة {invoice_no}",
                        "created_at": now
                    })

            # القيود الأساسية:
            # نقد/عملاء مدين
            # مبيعات دائن
            # ضريبة دائن
            # تكلفة مبيعات مدين
            # مخزون دائن

            lines = []

            if paid > 0:
                lines.append({
                    "account_code": "1100",
                    "debit": paid,
                    "credit": 0,
                    "description": "تحصيل البيع"
                })

            if due > 0:
                lines.append({
                    "account_code": "1300",
                    "debit": due,
                    "credit": 0,
                    "description": "ذمة العميل"
                })

            lines.append({
                "account_code": "4100",
                "debit": 0,
                "credit": subtotal,
                "description": "إيراد المبيعات"
            })

            if tax > 0:
                lines.append({
                    "account_code": "2200",
                    "debit": 0,
                    "credit": tax,
                    "description": "ضريبة القيمة المضافة - مخرجات"
                })

            lines.append({
                "account_code": "5100",
                "debit": cost_total,
                "credit": 0,
                "description": "تكلفة البضاعة المباعة"
            })

            lines.append({
                "account_code": "1400",
                "debit": 0,
                "credit": cost_total,
                "description": "خروج المخزون"
            })

            self._journal(
                con,
                f"فاتورة بيع {invoice_no}",
                lines,
                "SALE",
                sale_id
            )

            return {
                "sale_id": sale_id,
                "invoice_number": invoice_no,
                "subtotal": float(subtotal),
                "tax": float(tax),
                "total": float(total),
                "paid": float(paid),
                "due": float(due),
                "cost": float(cost_total)
            }

    def dashboard(self):
        with self.connect() as con:
            result = {}
            tables = {
                "products": "المنتجات",
                "customers": "العملاء",
                "suppliers": "الموردون",
                "sales": "المبيعات",
                "purchase_orders": "المشتريات",
                "stock_movements": "حركات المخزون",
                "journal_entries": "القيود المحاسبية"
            }

            for table, label in tables.items():
                if self._exists(con, table):
                    result[label] = con.execute(
                        f'SELECT COUNT(*) c FROM "{table}"'
                    ).fetchone()["c"]
                else:
                    result[label] = 0

            return result

    def health_check(self):
        with self.connect() as con:
            fk = con.execute("PRAGMA foreign_key_check").fetchall()
            integrity = con.execute("PRAGMA integrity_check").fetchone()[0]

            return {
                "database": "OK",
                "integrity": integrity == "ok",
                "foreign_keys": len(fk) == 0,
                "dashboard": self.dashboard()
            }
