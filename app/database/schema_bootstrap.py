"""تهيئة مخطط قاعدة البيانات المرجعي والتشغيلي بصورة آمنة."""
from __future__ import annotations

import json
from pathlib import Path
from sqlalchemy import text

from app.services.enterprise_completion_service import EnterpriseCompletionService

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_FILE = ROOT / "database" / "metadata" / "database_schema.json"


def _quote(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


def _ensure_legacy_columns(session) -> None:
    """يضيف أعمدة التشغيل إلى الجداول القديمة دون إسقاط أو إعادة إنشاء."""
    tables = {r[0] for r in session.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()}
    if "workflow_steps" in tables:
        cols = {r[1] for r in session.connection().exec_driver_sql("PRAGMA table_info(workflow_steps)").fetchall()}
        additions = {
            "workflow_code": "TEXT",
            "step_no": "INTEGER",
            "step_name": "TEXT",
            "role_code": "TEXT",
            "is_required": "INTEGER DEFAULT 1",
            "created_at": "TEXT",
        }
        for column, typ in additions.items():
            if column not in cols:
                session.execute(text(f"ALTER TABLE workflow_steps ADD COLUMN {_quote(column)} {typ}"))


def ensure_reference_schema(session) -> int:
    created = 0
    if SCHEMA_FILE.exists():
        data = json.loads(SCHEMA_FILE.read_text(encoding="utf-8-sig"))
        tables = data.get("tables") or {}
        for table_name, spec in tables.items():
            exists = session.execute(
                text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:name"),
                {"name": table_name},
            ).scalar()
            if exists:
                continue

            definitions = []
            columns = spec.get("columns", [])
            primary_columns = [column for column in columns if column.get("primary_key")]
            for column in columns:
                name = _quote(column["name"])
                typ = str(column.get("type") or "TEXT")
                definition = f"{name} {typ}"
                if len(primary_columns) == 1 and column.get("primary_key"):
                    definition += " PRIMARY KEY"
                    if typ.upper() == "INTEGER":
                        definition += " AUTOINCREMENT"
                if column.get("not_null") and not column.get("primary_key"):
                    definition += " NOT NULL"
                default = column.get("default")
                if default is not None:
                    definition += f" DEFAULT {default}"
                definitions.append(definition)
            if len(primary_columns) > 1:
                definitions.append(
                    "PRIMARY KEY (" + ", ".join(_quote(column["name"]) for column in primary_columns) + ")"
                )
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

    _ensure_legacy_columns(session)
    EnterpriseCompletionService.ensure(session)
    EnterpriseCompletionService.sync_inventory_mirror(session)
    return created
