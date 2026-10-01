from datetime import datetime
from decimal import Decimal
from sqlalchemy import text
from app.database.connection import get_session


class PartyMasterService:
    """خدمة موحدة لإنشاء وتعديل العملاء والموردين مع الحقول التشغيلية الكاملة."""

    OPTIONAL_FIELDS = {
        "customers": {
            "mobile": "TEXT",
            "payment_terms": "TEXT",
            "currency_code": "VARCHAR(10) DEFAULT 'SAR'",
            "notes": "TEXT",
            "accounting_account_id": "INTEGER",
        },
        "suppliers": {
            "mobile": "TEXT",
            "payment_terms": "TEXT",
            "currency_code": "VARCHAR(10) DEFAULT 'SAR'",
            "notes": "TEXT",
            "accounting_account_id": "INTEGER",
        },
    }

    @staticmethod
    def _columns(session, table):
        return {
            row[1]
            for row in session.execute(text(f"PRAGMA table_info({table})")).fetchall()
        }

    @classmethod
    def ensure_optional_fields(cls, session=None):
        """يضيف فقط الحقول التشغيلية المفقودة، دون حذف أو إعادة إنشاء أي بيانات."""
        def apply(s):
            for table, fields in cls.OPTIONAL_FIELDS.items():
                cols = cls._columns(s, table)
                if not cols:
                    raise ValueError(f"الجدول غير موجود: {table}")
                for name, definition in fields.items():
                    if name not in cols:
                        s.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {definition}"))

        if session is not None:
            apply(session)
            return
        with get_session() as s:
            apply(s)
            s.commit()

    @classmethod
    def _create(cls, table, code_field, code, name, details=None, session=None):
        if table not in ("customers", "suppliers"):
            raise ValueError("نوع الطرف غير مسموح")

        details = dict(details or {})
        details["code"] = str(code or "").strip()
        details["name"] = str(name or "").strip()
        if not details["code"] or not details["name"]:
            raise ValueError("الكود والاسم مطلوبان")

        def work(s):
            cls.ensure_optional_fields(s)
            cols = cls._columns(s, table)
            if not cols:
                raise ValueError(f"الجدول غير موجود: {table}")

            exists = s.execute(
                text(f"SELECT id FROM {table} WHERE {code_field}=:code LIMIT 1"),
                {"code": details["code"]},
            ).fetchone()
            if exists:
                raise ValueError("الكود مستخدم مسبقًا")

            data = {
                code_field: details["code"],
                "name": details["name"],
                "phone": details.get("phone"),
                "mobile": details.get("mobile"),
                "email": details.get("email"),
                "tax_number": details.get("tax_number"),
                "credit_limit": float(details.get("credit_limit") or 0),
                "is_active": 1 if details.get("is_active", True) else 0,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "customer_type" if table == "customers" else "supplier_type":
                    details.get("party_type") or ("individual" if table == "customers" else "local"),
                "group_id": details.get("group_id"),
                "payment_terms": details.get("payment_terms"),
                "currency_code": details.get("currency_code") or "SAR",
                "notes": details.get("notes"),
                "accounting_account_id": details.get("accounting_account_id"),
            }
            if table == "suppliers":
                data["address"] = details.get("address")

            data = {k: v for k, v in data.items() if k in cols}
            keys = ", ".join(data)
            binds = ", ".join(":" + k for k in data)
            s.execute(text(f"INSERT INTO {table} ({keys}) VALUES ({binds})"), data)
            entity_id = int(s.execute(text("SELECT last_insert_rowid()")).scalar())

            address = str(details.get("address") or "").strip()
            if table == "customers" and address:
                address_cols = cls._columns(s, "customer_addresses")
                if {"customer_id", "address"}.issubset(address_cols):
                    s.execute(
                        text(
                            "INSERT INTO customer_addresses "
                            "(customer_id,address,address_type) "
                            "VALUES (:id,:address,'main')"
                        ),
                        {"id": entity_id, "address": address},
                    )
            return entity_id

        if session is not None:
            return work(session)
        with get_session() as s:
            try:
                entity_id = work(s)
                s.commit()
                return entity_id
            except Exception:
                s.rollback()
                raise

    @classmethod
    def create_customer(cls, code, name, phone=None, credit_limit=0, **details):
        details.update(phone=phone, credit_limit=credit_limit)
        return cls._create("customers", "customer_code", code, name, details)

    @classmethod
    def create_supplier(cls, code, name, phone=None, credit_limit=0, **details):
        details.update(phone=phone, credit_limit=credit_limit)
        return cls._create("suppliers", "supplier_code", code, name, details)

    @classmethod
    def update_party(cls, table, party_id, **details):
        if table not in ("customers", "suppliers"):
            raise ValueError("نوع الطرف غير مسموح")

        code_field = "customer_code" if table == "customers" else "supplier_code"

        def work(s):
            cls.ensure_optional_fields(s)
            cols = cls._columns(s, table)
            current = s.execute(
                text(f"SELECT * FROM {table} WHERE id=:id"),
                {"id": party_id},
            ).fetchone()
            if not current:
                raise ValueError("الطرف غير موجود")

            data = {
                code_field: str(details.get("code") or current._mapping.get(code_field) or "").strip(),
                "name": str(details.get("name") or current._mapping.get("name") or "").strip(),
                "phone": details.get("phone", current._mapping.get("phone")),
                "email": details.get("email", current._mapping.get("email")),
                "tax_number": details.get("tax_number", current._mapping.get("tax_number")),
                "credit_limit": float(details.get("credit_limit", current._mapping.get("credit_limit") or 0)),
                "is_active": 1 if details.get("is_active", current._mapping.get("is_active", 1)) else 0,
                "group_id": details.get("group_id", current._mapping.get("group_id")),
                "payment_terms": details.get("payment_terms", current._mapping.get("payment_terms")),
                "currency_code": details.get("currency_code", current._mapping.get("currency_code") or "SAR"),
                "notes": details.get("notes", current._mapping.get("notes")),
                "accounting_account_id": details.get(
                    "accounting_account_id",
                    current._mapping.get("accounting_account_id"),
                ),
                "updated_at": datetime.now().isoformat(),
            }
            type_field = "customer_type" if table == "customers" else "supplier_type"
            if type_field in cols:
                data[type_field] = details.get(
                    "party_type",
                    current._mapping.get(type_field),
                )
            if table == "suppliers" and "address" in cols:
                data["address"] = details.get("address", current._mapping.get("address"))

            data = {k: v for k, v in data.items() if k in cols}
            if not data["name"] or not data[code_field]:
                raise ValueError("الكود والاسم مطلوبان")

            duplicate = s.execute(
                text(
                    f"SELECT id FROM {table} "
                    f"WHERE {code_field}=:code AND id<>:id LIMIT 1"
                ),
                {"code": data[code_field], "id": party_id},
            ).fetchone()
            if duplicate:
                raise ValueError("الكود مستخدم مسبقًا")

            assignments = ", ".join(f"{k}=:{k}" for k in data)
            data["id"] = party_id
            s.execute(
                text(f"UPDATE {table} SET {assignments} WHERE id=:id"),
                data,
            )

            if table == "customers" and "address" in details:
                address = str(details.get("address") or "").strip()
                address_cols = cls._columns(s, "customer_addresses")
                if {"customer_id", "address"}.issubset(address_cols):
                    existing = s.execute(
                        text(
                            "SELECT id FROM customer_addresses "
                            "WHERE customer_id=:id AND address_type='main' "
                            "ORDER BY id LIMIT 1"
                        ),
                        {"id": party_id},
                    ).fetchone()
                    if existing:
                        if address:
                            s.execute(
                                text(
                                    "UPDATE customer_addresses SET address=:address "
                                    "WHERE id=:address_id"
                                ),
                                {"address": address, "address_id": existing[0]},
                            )
                        else:
                            s.execute(
                                text("DELETE FROM customer_addresses WHERE id=:address_id"),
                                {"address_id": existing[0]},
                            )
                    elif address:
                        s.execute(
                            text(
                                "INSERT INTO customer_addresses "
                                "(customer_id,address,address_type) "
                                "VALUES (:id,:address,'main')"
                            ),
                            {"id": party_id, "address": address},
                        )
            return party_id

        if session is not None:
            return work(session)
        with get_session() as s:
            try:
                result = work(s)
                s.commit()
                return result
            except Exception:
                s.rollback()
                raise


    @classmethod
    def deactivate_party(cls, table, party_id):
        if table not in ("customers","suppliers"):
            raise ValueError("نوع الطرف غير مسموح")
        with get_session() as s:
            row=s.execute(text(f"SELECT current_balance FROM {table} WHERE id=:id"),{"id":int(party_id)}).fetchone()
            if not row:
                raise ValueError("الطرف غير موجود")
            balance=float(row[0] or 0)
            if abs(balance) > 0.0001:
                raise ValueError("لا يمكن حذف/تعطيل طرف عليه رصيد. يجب تسوية الرصيد أولًا.")
            result=s.execute(text(f"UPDATE {table} SET is_active=0, updated_at=CURRENT_TIMESTAMP WHERE id=:id"),{"id":int(party_id)})
            if result.rowcount != 1:
                raise ValueError("تعذر تعطيل الطرف")
            s.commit()
