
from app.database.connection import database_health
from app.services.system_service import (
    get_system_summary,
    get_financial_summary,
)

def test_database_health():
    result = database_health()
    assert result["integrity"] == "ok"
    assert result["foreign_key_errors"] == 0
    assert result["healthy"] is True

def test_system_summary():
    result = get_system_summary()
    assert result["products"] >= 0
    assert result["customers"] >= 0
    assert result["suppliers"] >= 0

def test_financial_summary():
    result = get_financial_summary()
    assert "inventory" in result
    assert "sales" in result
    assert "cogs" in result
