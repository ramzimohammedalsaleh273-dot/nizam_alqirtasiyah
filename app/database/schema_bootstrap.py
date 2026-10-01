"""تهيئة مخطط قاعدة البيانات المرجعي من ملف metadata المولّد للمشروع.

لا تحذف هذه الوظيفة أي بيانات ولا تعيد إنشاء جدول موجود؛ هدفها فقط ضمان أن
التثبيت الجديد أو بيئة الاختبار تملك الجداول التي يعتمد عليها النظام.
"""
from __future__ import annotations

import json
from pathlib import Path
from sqlalchemy import text


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_FILE = ROOT / "database" / "metadata" / "database_schema.json"


def _quote(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


def ensure_reference_schema(session) -> int:
    if not SCHEMA_FILE.exists():
        return 0

    data = json.loads(SCHEMA_FILE.read_text(encoding="utf-8-sig"))
    tables = data.get("tables") or {}
    created = 0

    for table_name, spec in tables.items():
        exists = session.execute(
            text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:name"),
            {"name": table_name},
        ).scalar()
        if exists:
            continue

        definitions = []
        for column in spec.get("columns", []):
            name = _quote(column["name"])
            typ = str(column.get("type") or "TEXT")
            definition = f"{name} {typ}"
            if column.get("primary_key"):
                definition += " PRIMARY KEY"
                if typ.upper() == "INTEGER":
                    definition += " AUTOINCREMENT"
            if column.get("not_null") and not column.get("primary_key"):
                definition += " NOT NULL"
            default = column.get("default")
            if default is not None:
                definition += f" DEFAULT {default}"
            definitions.append(definition)

        for fk in spec.get("foreign_keys", []):
            definitions.append(
                f"FOREIGN KEY ({_quote(fk['column'])}) "
                f"REFERENCES {_quote(fk['table'])}({_quote(fk['references'])})"
            )

        if definitions:
            session.execute(
                text(
                    f"CREATE TABLE IF NOT EXISTS {_quote(table_name)} "
                    f"({', '.join(definitions)})"
                )
            )
            created += 1

    return created
