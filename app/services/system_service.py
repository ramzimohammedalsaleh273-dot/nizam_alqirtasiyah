
from sqlalchemy import text
from app.database.connection import get_session, database_health

def get_system_summary():
    with get_session() as session:

        tables={r[0] for r in session.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).all()}
        def count(table):
            if table not in tables:
                return 0
            return session.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar() or 0

        summary = {
            "products": count("products"),
            "customers": count("customers"),
            "suppliers": count("suppliers"),
            "employees": count("employees"),
            "sales": count("sales"),
            "purchase_invoices": count("purchase_invoices"),
            "stock": count("stock_balances"),
            "journal_entries": count("journal_entries"),
            "low_stock": (
                session.execute(text("""SELECT COUNT(*) FROM products p LEFT JOIN stock_balances st ON st.product_id=p.id WHERE p.is_active=1 AND COALESCE(st.quantity - st.reserved_quantity,0) <= COALESCE(NULLIF(p.reorder_point,0),p.min_stock,0)""")).scalar() or 0
                if {"products","stock_balances"}.issubset(tables) else 0
            ),
        }

        return summary

def get_financial_summary():
    with get_session() as session:

        tables={r[0] for r in session.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).all()}
        def balance(code):
            if not {"journal_entry_lines","accounts"}.issubset(tables):
                return 0.0
            value = session.execute(text("""
                SELECT COALESCE(SUM(j.debit),0)-COALESCE(SUM(j.credit),0)
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
