from decimal import Decimal
from app.services.tax_service import TaxService

def test_tax_engine_default_rate():
    r=TaxService.calculate("100")
    assert r["base"] == 100.0
    assert r["tax"] == 15.0
    assert r["total"] == 115.0

def test_tax_engine_custom_rate():
    r=TaxService.calculate(100, "5")
    assert r["tax"] == 5.0
    assert r["total"] == 105.0
