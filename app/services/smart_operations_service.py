from sqlalchemy import text
from app.database.connection import get_session


class SmartOperationsService:
    """مؤشرات تشغيلية مباشرة تساعد المستخدم على معرفة ما يحتاجه الآن."""

    @staticmethod
    def _exists(s, table):
        return bool(s.execute(
            text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:name"),
            {"name": table},
        ).scalar())

    @classmethod
    def snapshot(cls):
        with get_session() as s:
            result = {}
            if cls._exists(s, "products") and cls._exists(s, "stock"):
                result["low_stock"] = int(s.execute(text("""
                    SELECT COUNT(*) FROM products p
                    LEFT JOIN stock st ON st.product_id=p.id
                    WHERE p.is_active=1
                      AND COALESCE(st.available_quantity,0) <= COALESCE(NULLIF(p.reorder_point,0),p.min_stock,0)
                """)).scalar() or 0)
            else:
                result["low_stock"] = 0

            if cls._exists(s, "sales"):
                result["customer_due"] = float(s.execute(text(
                    "SELECT COALESCE(SUM(due_amount),0) FROM sales"
                )).scalar() or 0)
            else:
                result["customer_due"] = 0

            if cls._exists(s, "purchase_invoices"):
                result["supplier_due"] = float(s.execute(text(
                    "SELECT COALESCE(SUM(due_amount),0) FROM purchase_invoices"
                )).scalar() or 0)
            else:
                result["supplier_due"] = 0

            if cls._exists(s, "journal_entries"):
                result["journal_count"] = int(s.execute(text(
                    "SELECT COUNT(*) FROM journal_entries"
                )).scalar() or 0)
                result["unbalanced"] = int(s.execute(text("""
                    SELECT COUNT(*) FROM (
                        SELECT je.id
                        FROM journal_entries je
                        JOIN journal_entry_lines jl ON jl.journal_entry_id=je.id
                        GROUP BY je.id
                        HAVING ROUND(COALESCE(SUM(jl.debit),0),2) <> ROUND(COALESCE(SUM(jl.credit),0),2)
                    )
                """)).scalar() or 0) if cls._exists(s, "journal_entry_lines") else 0
            else:
                result["journal_count"] = result["unbalanced"] = 0

            if cls._exists(s, "audit_logs"):
                result["audit_events"] = int(s.execute(text(
                    "SELECT COUNT(*) FROM audit_logs"
                )).scalar() or 0)
            else:
                result["audit_events"] = 0

            return result
