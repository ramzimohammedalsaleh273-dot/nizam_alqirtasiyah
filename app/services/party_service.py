from sqlalchemy import text
from app.database.connection import get_session
from app.services.party_master_service import PartyMasterService


class PartyService:

    @staticmethod
    def _load(table, code_field, limit=200):
        PartyMasterService.ensure_optional_fields()
        with get_session() as s:
            group_table = "customer_groups" if table == "customers" else "supplier_groups"
            address_expr = (
                "(SELECT ca.address FROM customer_addresses ca "
                "WHERE ca.customer_id=p.id AND ca.address_type='main' "
                "ORDER BY ca.id LIMIT 1)"
                if table == "customers"
                else "p.address"
            )
            type_field = "customer_type" if table == "customers" else "supplier_type"
            rows = s.execute(
                text(f"""
                    SELECT
                        p.id,
                        p.{code_field} AS party_code,
                        p.name,
                        p.{type_field} AS party_type,
                        p.phone,
                        p.mobile,
                        p.email,
                        p.tax_number,
                        p.credit_limit,
                        p.current_balance,
                        p.group_id,
                        g.name AS group_name,
                        {address_expr} AS address,
                        p.payment_terms,
                        p.currency_code,
                        p.notes,
                        p.accounting_account_id,
                        p.is_active
                    FROM {table} p
                    LEFT JOIN {group_table} g ON g.id=p.group_id
                    ORDER BY p.id
                    LIMIT :limit
                """),
                {"limit": limit},
            ).fetchall()
            return [dict(r._mapping) for r in rows]

    @staticmethod
    def customers(limit=200):
        return PartyService._load("customers", "customer_code", limit)

    @staticmethod
    def suppliers(limit=200):
        return PartyService._load("suppliers", "supplier_code", limit)

    @staticmethod
    def groups(supplier=False):
        table = "supplier_groups" if supplier else "customer_groups"
        with get_session() as s:
            rows = s.execute(
                text(f"SELECT id,name FROM {table} ORDER BY name")
            ).fetchall()
            return [dict(r._mapping) for r in rows]

    @staticmethod
    def get_party(table, party_id):
        if table not in ("customers", "suppliers"):
            raise ValueError("نوع الطرف غير مسموح")
        rows = PartyService._load(
            table,
            "customer_code" if table == "customers" else "supplier_code",
            100000,
        )
        return next((r for r in rows if int(r["id"]) == int(party_id)), None)

    @staticmethod
    def customer_balance(customer_id):
        with get_session() as s:
            return float(
                s.execute(
                    text("""
                        SELECT COALESCE(current_balance,0)
                        FROM customers
                        WHERE id=:id
                    """),
                    {"id": customer_id},
                ).scalar() or 0
            )
