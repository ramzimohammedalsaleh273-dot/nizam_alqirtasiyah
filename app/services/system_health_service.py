from sqlalchemy import text
from app.database.connection import get_session


class SystemHealthService:
    """فحص شامل نسبيًا لسلامة البنية والبيانات التشغيلية دون افتراض أعمدة غير موجودة."""

    REQUIRED_TABLES = (
        "products", "customers", "suppliers", "sales", "sale_items",
        "purchase_invoices", "stock", "stock_movements",
        "accounts", "journal_entries", "journal_entry_lines",
        "audit_logs",
    )

    @staticmethod
    def _columns(session, table):
        return {
            row[1]
            for row in session.execute(
                text(f'PRAGMA table_info("{table}")')
            ).fetchall()
        }

    @classmethod
    def run_all(cls):
        with get_session() as s:
            checks = []
            tables = {
                row[0] for row in s.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table'")
                ).fetchall()
            }

            missing = [x for x in cls.REQUIRED_TABLES if x not in tables]
            checks.append((
                "الجداول الأساسية",
                not missing,
                "مفقود: " + ", ".join(missing) if missing else "كل الجداول الأساسية موجودة"
            ))

            integrity = str(
                s.execute(text("PRAGMA integrity_check")).scalar() or ""
            )
            checks.append((
                "سلامة قاعدة SQLite",
                integrity.lower() == "ok",
                integrity
            ))

            fk_rows = s.execute(text("PRAGMA foreign_key_check")).fetchall()
            checks.append((
                "سلامة المفاتيح الأجنبية",
                not fk_rows,
                f"عدد المخالفات: {len(fk_rows)}"
            ))

            if "products" in tables:
                cols = cls._columns(s, "products")
                if "sku" in cols:
                    dup = s.execute(text("""
                        SELECT COUNT(*) FROM (
                            SELECT sku FROM products
                            WHERE sku IS NOT NULL AND TRIM(sku)<>''
                            GROUP BY sku HAVING COUNT(*)>1
                        )
                    """)).scalar() or 0
                    checks.append((
                        "عدم تكرار رموز الأصناف",
                        int(dup) == 0,
                        f"مجموعات مكررة: {dup}"
                    ))

                required_product_cols = {"id", "name_ar", "sku"}
                missing_product_cols = sorted(required_product_cols - cols)
                checks.append((
                    "بنية جدول الأصناف",
                    not missing_product_cols,
                    "الأعمدة الأساسية موجودة"
                    if not missing_product_cols
                    else "مفقود: " + ", ".join(missing_product_cols)
                ))

            if "stock" in tables:
                stock_cols = cls._columns(s, "stock")
                quantity_expr = (
                    "COALESCE(available_quantity, quantity, 0)"
                    if {"available_quantity", "quantity"} <= stock_cols
                    else "COALESCE(available_quantity, 0)"
                    if "available_quantity" in stock_cols
                    else "COALESCE(quantity, 0)"
                    if "quantity" in stock_cols
                    else "0"
                )
                negative = s.execute(
                    text(f"SELECT COUNT(*) FROM stock WHERE {quantity_expr} < 0")
                ).scalar() or 0
                checks.append((
                    "عدم وجود مخزون سالب",
                    int(negative) == 0,
                    f"سجلات سالبة: {negative}"
                ))
                checks.append((
                    "بنية جدول المخزون",
                    bool({"product_id"} <= stock_cols and ({"quantity"} <= stock_cols or {"available_quantity"} <= stock_cols)),
                    "الأعمدة التشغيلية الأساسية موجودة"
                    if bool({"product_id"} <= stock_cols and ({"quantity"} <= stock_cols or {"available_quantity"} <= stock_cols))
                    else "أعمدة المخزون الأساسية ناقصة"
                ))

            if "journal_entries" in tables and "journal_entry_lines" in tables:
                je_cols = cls._columns(s, "journal_entries")
                line_cols = cls._columns(s, "journal_entry_lines")
                if "status" in je_cols and "journal_entry_id" in line_cols:
                    unbalanced = s.execute(text("""
                        SELECT COUNT(*) FROM (
                            SELECT je.id
                            FROM journal_entries je
                            JOIN journal_entry_lines jel
                              ON jel.journal_entry_id=je.id
                            WHERE je.status='POSTED'
                            GROUP BY je.id
                            HAVING ROUND(COALESCE(SUM(jel.debit),0),2)
                                <> ROUND(COALESCE(SUM(jel.credit),0),2)
                        )
                    """)).scalar() or 0
                    checks.append((
                        "توازن القيود المرحلة",
                        int(unbalanced) == 0,
                        f"قيود غير متوازنة: {unbalanced}"
                    ))
                else:
                    checks.append((
                        "بنية المحاسبة",
                        False,
                        "أعمدة حالة القيد أو ربط سطور القيد غير مكتملة"
                    ))

            # فحوصات اتساق المستندات التشغيلية.
            for table, column, label in (
                ("sales", "invoice_number", "أرقام فواتير المبيعات"),
                ("purchase_invoices", "invoice_number", "أرقام فواتير المشتريات"),
                ("journal_entries", "entry_number", "أرقام القيود"),
            ):
                if table in tables:
                    cols = cls._columns(s, table)
                    if column in cols:
                        duplicates = s.execute(text(f"""
                            SELECT COUNT(*) FROM (
                                SELECT "{column}"
                                FROM "{table}"
                                WHERE "{column}" IS NOT NULL
                                  AND TRIM(CAST("{column}" AS TEXT)) <> ''
                                GROUP BY "{column}"
                                HAVING COUNT(*) > 1
                            )
                        """)).scalar() or 0
                        checks.append((
                            f"عدم تكرار {label}",
                            int(duplicates) == 0,
                            f"مجموعات مكررة: {duplicates}"
                        ))

            # فحص عناصر المبيعات التي تشير إلى منتجات غير موجودة.
            if "sale_items" in tables and "products" in tables:
                item_cols = cls._columns(s, "sale_items")
                if "product_id" in item_cols:
                    orphan_sales = s.execute(text("""
                        SELECT COUNT(*)
                        FROM sale_items si
                        LEFT JOIN products p ON p.id=si.product_id
                        WHERE p.id IS NULL
                    """)).scalar() or 0
                    checks.append((
                        "سلامة ربط أصناف المبيعات",
                        int(orphan_sales) == 0,
                        f"عناصر بلا منتج: {orphan_sales}"
                    ))

            if "stock" in tables and "products" in tables:
                stock_cols = cls._columns(s, "stock")
                if "product_id" in stock_cols:
                    orphan_stock = s.execute(text("""
                        SELECT COUNT(*)
                        FROM stock st
                        LEFT JOIN products p ON p.id=st.product_id
                        WHERE p.id IS NULL
                    """)).scalar() or 0
                    checks.append((
                        "سلامة ربط المخزون",
                        int(orphan_stock) == 0,
                        f"سجلات مخزون بلا منتج: {orphan_stock}"
                    ))

            # فحص اتساق إجماليات المبيعات عند توفر الأعمدة.
            if "sales" in tables and "sale_items" in tables:
                sales_cols = cls._columns(s, "sales")
                item_cols = cls._columns(s, "sale_items")
                if {"id", "subtotal"} <= sales_cols and {"sale_id", "line_total"} <= item_cols:
                    mismatch = s.execute(text("""
                        SELECT COUNT(*)
                        FROM sales sa
                        WHERE ABS(
                            COALESCE(sa.subtotal,0) -
                            COALESCE((
                                SELECT SUM(COALESCE(si.line_total,0))
                                FROM sale_items si
                                WHERE si.sale_id=sa.id
                            ),0)
                        ) > 0.02
                    """)).scalar() or 0
                    checks.append((
                        "اتساق إجماليات المبيعات",
                        int(mismatch) == 0,
                        f"فواتير مختلفة عن مجموع السطور: {mismatch}"
                    ))

            # فحص أنظمة مكررة معروفة من مراحل البناء؛ لا يفشل النظام بسبب وجودها،
            # لكنه يجعلها مرئية حتى تُدمج تدريجيًا.
            duplicate_groups = (
                ("المخزون", ("stock", "stock_balances")),
                ("الحسابات", ("accounts", "chart_of_accounts")),
                ("الفترات", ("accounting_periods", "fiscal_periods")),
                ("التدقيق", ("audit_log", "audit_logs", "system_audit_log", "security_audit")),
                ("الجلسات", ("user_sessions", "erp_login_sessions")),
                ("الصلاحيات", ("roles", "permissions", "role_permissions", "user_roles",
                               "erp_roles", "erp_permissions", "erp_role_permissions", "erp_user_roles")),
            )
            for label, candidates in duplicate_groups:
                present = [name for name in candidates if name in tables]
                if len(present) > 1:
                    checks.append((
                        f"كشف ازدواجية {label}",
                        True,
                        "موجودة أنظمة متعددة تحتاج توحيدًا: " + ", ".join(present)
                    ))

            return checks

    @classmethod
    def summary(cls):
        checks = cls.run_all()
        blocking = [
            (name, ok, details)
            for name, ok, details in checks
            if not ok
        ]
        return {
            "healthy": not blocking,
            "checks": checks,
            "blocking_issues": blocking,
        }
