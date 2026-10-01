from sqlalchemy import text


class AuditService:
    """سجل تدقيق موحد للعمليات التي ينفذها النظام مع توافق المخططات القديمة."""

    @staticmethod
    def log(session, action, entity=None, entity_id=None, username=None):
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                action TEXT NOT NULL,
                entity TEXT,
                entity_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """))
        cols = {r[1] for r in session.connection().exec_driver_sql("PRAGMA table_info(audit_logs)").fetchall()}
        values = {
            "username": username,
            "action": action,
            "entity": entity,
            "entity_id": entity_id,
        }
        fields = [k for k in ("username", "action", "entity", "entity_id") if k in cols]
        if not fields:
            return
        params = {k: values[k] for k in fields}
        placeholders = ",".join(":"+k for k in fields)
        session.execute(
            text(f"INSERT INTO audit_logs({','.join(fields)},created_at) VALUES({placeholders},CURRENT_TIMESTAMP)"),
            params,
        )
