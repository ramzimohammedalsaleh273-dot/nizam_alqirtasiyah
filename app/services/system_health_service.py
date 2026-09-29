from sqlalchemy import text
from app.database.connection import get_session


class SystemHealthService:
    """فحوصات تشغيلية سريعة لاكتشاف مشاكل البيانات قبل اعتماد النظام."""

    REQUIRED_TABLES = (
        "products", "customers", "suppliers", "sales", "sale_items",
        "purchase_invoices", "stock", "stock_movements",
        "accounts", "journal_entries", "journal_entry_lines",
        "audit_logs",
    )

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
            checks.append(("الجداول الأساسية", not missing, "مفقود: " + ", ".join(missing) if missing else "كل الجداول موجودة"))

            integrity = str(s.execute(text("PRAGMA integrity_check")).scalar() or "")
            checks.append(("سلامة قاعدة SQLite", integrity.lower() == "ok", integrity))

            fk_rows = s.execute(text("PRAGMA foreign_key_check")).fetchall()
            checks.append(("سلامة المفاتيح الأجنبية", not fk_rows, f"عدد المخالفات: {len(fk_rows)}"))

            if "products" in tables:
                dup = s.execute(text("""
                    SELECT COUNT(*) FROM (
                        SELECT sku FROM products
                        WHERE sku IS NOT NULL AND TRIM(sku)<>''
                        GROUP BY sku HAVING COUNT(*)>1
                    )
                """)).scalar() or 0
                checks.append(("عدم تكرار رموز الأصناف", int(dup) == 0, f"مجموعات مكررة: {dup}"))

            if "stock" in tables:
                negative = s.execute(text("""
                    SELECT COUNT(*) FROM stock
                    WHERE COALESCE(available_quantity, quantity, 0) < 0
                """)).scalar() or 0
                checks.append(("عدم وجود مخزون سالب", int(negative) == 0, f"سجلات سالبة: {negative}"))

            if "journal_entries" in tables and "journal_entry_lines" in tables:
                unbalanced = s.execute(text("""
                    SELECT COUNT(*) FROM (
                        SELECT je.id
                        FROM journal_entries je
                        JOIN journal_entry_lines jel ON jel.journal_entry_id=je.id
                        WHERE je.status='POSTED'
                        GROUP BY je.id
                        HAVING ROUND(COALESCE(SUM(jel.debit),0),2) <> ROUND(COALESCE(SUM(jel.credit),0),2)
                    )
                """)).scalar() or 0
                checks.append(("توازن القيود المرحلة", int(unbalanced) == 0, f"قيود غير متوازنة: {unbalanced}"))

            return checks

    @classmethod
    def summary(cls):
        checks = cls.run_all()
        return {"healthy": all(ok for _, ok, _ in checks), "checks": checks}
