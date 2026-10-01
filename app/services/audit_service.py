from sqlalchemy import text


class AuditService:
    """سجل تدقيق موحد للعمليات مع توافق أسماء الأعمدة القديمة والجديدة."""

    @staticmethod
    def log(session, action, entity=None, entity_id=None, username=None):
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                user_id INTEGER,
                action TEXT NOT NULL,
                module TEXT,
                entity_type TEXT,
                entity TEXT,
                entity_id INTEGER,
                details TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """))
        cols = {r[1] for r in session.connection().exec_driver_sql("PRAGMA table_info(audit_logs)").fetchall()}
        values = {
            "username": username,
            "user_id": int(username) if str(username).isdigit() else None if username is not None else None,
            "action": action,
            "module": (str(entity).split("_", 1)[0] if entity else None),
            "entity_type": entity,
            "entity": entity,
            "entity_id": entity_id,
        }
        fields = [k for k in ("username", "user_id", "action", "module", "entity_type", "entity", "entity_id") if k in cols]
        if "action" not in fields:
            return
        params = {k: values[k] for k in fields}
        placeholders = ",".join(":"+k for k in fields)
        session.execute(
            text(f"INSERT INTO audit_logs({','.join(fields)},created_at) VALUES({placeholders},CURRENT_TIMESTAMP)"),
            params,
        )
