from sqlalchemy import text


class AuditService:
    """سجل تدقيق موحد للعمليات التي ينفذها النظام."""

    @staticmethod
    def log(session, action, entity=None, entity_id=None, username=None):
        session.execute(
            text("""
                INSERT INTO audit_logs
                (username, action, entity, entity_id, created_at)
                VALUES
                (:username, :action, :entity, :entity_id, CURRENT_TIMESTAMP)
            """),
            {
                "username": username,
                "action": action,
                "entity": entity,
                "entity_id": entity_id,
            },
        )
