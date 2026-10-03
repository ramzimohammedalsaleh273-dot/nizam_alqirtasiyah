from app.database.connection import get_session
from app.services.enterprise_completion_service import EnterpriseCompletionService


def test_enterprise_completion_schema_and_inventory_parity():
    with get_session() as session:
        EnterpriseCompletionService.ensure(session)
        EnterpriseCompletionService.sync_inventory_mirror(session)
        parity = EnterpriseCompletionService.inventory_parity(session)
        assert parity["ok"], parity
        for table in EnterpriseCompletionService.REQUIRED_TABLES:
            exists = session.execute(
                __import__("sqlalchemy").text(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=:name"
                ),
                {"name": table},
            ).scalar()
            assert exists, table
