from app.services.smart_operations_service import SmartOperationsService
from app.services.smart_insights_service import SmartInsightsService
from app.services.universal_search_service import UniversalSearchService


def test_smart_operations_snapshot_shape():
    data = SmartOperationsService.snapshot()
    assert {"low_stock", "customer_due", "supplier_due", "journal_count", "unbalanced", "audit_events"} <= set(data)


def test_universal_search_returns_list():
    rows = UniversalSearchService.search("دفتر")
    assert isinstance(rows, list)


def test_existing_product_has_360_profile():
    profile = SmartInsightsService.product_360(1)
    assert profile is not None
    assert profile["type"] == "product"
    assert "metrics" in profile


def test_product_service_exposes_stock_controls():
    from app.services.product_service import ProductService
    assert callable(ProductService.deactivate_product)
    assert callable(ProductService.adjust_quantity)


def test_party_service_exposes_safe_deactivation():
    from app.services.party_master_service import PartyMasterService
    assert callable(PartyMasterService.deactivate_party)
