from sqlalchemy import text
from app.database.connection import get_session
from app.services.enterprise_completion_service import EnterpriseCompletionService


class SystemValidationService:
    """فحص قبول تشغيلي حقيقي لقاعدة بيانات نظام القرطاسية."""

    REQUIRED_TABLES = (
        "products", "customers", "suppliers", "sales", "sale_items",
        "purchase_invoices", "purchase_invoice_items", "stock",
        "stock_balances", "stock_movements", "accounts", "journal_entries",
        "journal_entry_lines", "audit_logs", "purchase_requests",
        "purchase_request_items", "purchase_orders", "purchase_order_items",
        *EnterpriseCompletionService.REQUIRED_TABLES,
    )

    @staticmethod
    def run():
        checks = []
        with get_session() as s:
            c = s.connection()
            EnterpriseCompletionService.ensure(s)
            EnterpriseCompletionService.sync_inventory_mirror(s)
            s.commit()

            integrity = c.exec_driver_sql("PRAGMA integrity_check").scalar()
            checks.append(("سلامة SQLite", integrity == "ok", str(integrity)))
            fk = c.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
            checks.append(("المفاتيح الأجنبية", not fk, f"{len(fk)} أخطاء"))

            tables = {
                r[0] for r in c.exec_driver_sql(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            for table in SystemValidationService.REQUIRED_TABLES:
                checks.append((
                    f"جدول {table}", table in tables,
                    "موجود" if table in tables else "مفقود",
                ))

            if "journal_entries" in tables and "journal_entry_lines" in tables:
                bad = c.exec_driver_sql("""
                    SELECT je.id FROM journal_entries je
                    JOIN journal_entry_lines jl ON jl.journal_entry_id = je.id
                    WHERE je.status='POSTED'
                    GROUP BY je.id
                    HAVING ABS(SUM(COALESCE(jl.debit,0))-SUM(COALESCE(jl.credit,0))) > 0.01
                """).fetchall()
                checks.append(("توازن القيود المرحّلة", not bad, f"{len(bad)} قيود غير متوازنة"))
                orphan_lines = c.exec_driver_sql("""
                    SELECT COUNT(*) FROM journal_entry_lines jl
                    LEFT JOIN journal_entries je ON je.id=jl.journal_entry_id
                    WHERE je.id IS NULL
                """).scalar()
                checks.append(("قيود محاسبية بلا رأس", int(orphan_lines or 0) == 0, f"{int(orphan_lines or 0)} أسطر يتيمة"))

            if "sales" in tables:
                dup = c.exec_driver_sql("""
                    SELECT invoice_number FROM sales
                    WHERE invoice_number IS NOT NULL GROUP BY invoice_number HAVING COUNT(*) > 1
                """).fetchall()
                checks.append(("أرقام فواتير البيع", not dup, f"{len(dup)} مكررة"))

            if "purchase_invoices" in tables:
                cols = {r[1] for r in c.exec_driver_sql("PRAGMA table_info(purchase_invoices)").fetchall()}
                if "invoice_number" in cols:
                    dup_purchase = c.exec_driver_sql("""
                        SELECT invoice_number FROM purchase_invoices
                        WHERE invoice_number IS NOT NULL GROUP BY invoice_number HAVING COUNT(*) > 1
                    """).fetchall()
                    checks.append(("أرقام فواتير الشراء", not dup_purchase, f"{len(dup_purchase)} مكررة"))

            if "stock" in tables:
                negative = c.exec_driver_sql("SELECT COUNT(*) FROM stock WHERE COALESCE(quantity,0) < -0.000001").scalar()
                checks.append(("عدم وجود مخزون سالب", int(negative or 0) == 0, f"{int(negative or 0)} أرصدة سالبة"))

            parity = EnterpriseCompletionService.inventory_parity(s)
            checks.append(("تطابق stock مع stock_balances", parity["ok"], parity["detail"]))

            orphan_sales = c.exec_driver_sql("""
                SELECT COUNT(*) FROM sale_items si
                LEFT JOIN sales s ON s.id=si.sale_id WHERE s.id IS NULL
            """).scalar() if {"sale_items", "sales"}.issubset(tables) else 0
            checks.append(("بنود مبيعات بلا فاتورة", int(orphan_sales or 0) == 0, f"{int(orphan_sales or 0)} بنود يتيمة"))

            orphan_orders = c.exec_driver_sql("""
                SELECT COUNT(*) FROM purchase_order_items poi
                LEFT JOIN purchase_orders po ON po.id=poi.order_id WHERE po.id IS NULL
            """).scalar() if {"purchase_order_items", "purchase_orders"}.issubset(tables) else 0
            checks.append(("بنود أوامر شراء بلا أمر", int(orphan_orders or 0) == 0, f"{int(orphan_orders or 0)} بنود يتيمة"))

            audit_count = c.exec_driver_sql("SELECT COUNT(*) FROM audit_logs").scalar() if "audit_logs" in tables else -1
            checks.append(("سجل التدقيق قابل للقراءة", int(audit_count) >= 0, f"{int(audit_count)} سجل"))

        return {
            "healthy": all(x[1] for x in checks),
            "checks": [{"name": x[0], "ok": x[1], "detail": x[2]} for x in checks],
        }
