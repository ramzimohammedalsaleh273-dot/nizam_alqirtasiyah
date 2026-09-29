
from sqlalchemy import text
from app.database.connection import get_session, database_health

def get_system_summary():
    with get_session() as session:

        def count(table):
            return session.execute(
                text(f'SELECT COUNT(*) FROM "{table}"')
            ).scalar() or 0

        summary = {
            "products": count("products"),
            "customers": count("customers"),
            "suppliers": count("suppliers"),
            "employees": count("employees"),
            "sales": count("sales"),
            "purchase_invoices": count("purchase_invoices"),
            "stock": count("stock"),
            "journal_entries": count("journal_entries"),
        }

        return summary

def get_financial_summary():
    with get_session() as session:

        def balance(code):
            value = session.execute(text("""
                SELECT
                    COALESCE(SUM(j.debit),0)
                    -
                    COALESCE(SUM(j.credit),0)
                FROM journal_entry_lines j
                JOIN accounts a ON a.id=j.account_id
                WHERE a.account_code=:code
            """), {"code": code}).scalar()

            return round(float(value or 0), 2)

        return {
            "cash": balance("1100"),
            "banks": balance("1200"),
            "customers": balance("1300"),
            "inventory": balance("1400"),
            "suppliers": balance("2100"),
            "sales": balance("4100"),
            "cogs": balance("5100"),
        }

def get_health():
    return database_health()
