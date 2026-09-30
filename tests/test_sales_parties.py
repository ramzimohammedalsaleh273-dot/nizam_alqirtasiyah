from app.services.sales_service import SalesService
from app.services.purchase_service import PurchaseService
from app.services.party_service import PartyService
from app.services.party_master_service import PartyMasterService


def test_sales_list():
    rows = SalesService.list_sales()
    assert len(rows) >= 4


def test_purchase_list():
    rows = PurchaseService.list_purchases()
    assert len(rows) >= 6


def test_customers():
    rows = PartyService.customers()
    assert len(rows) >= 28


def test_suppliers():
    rows = PartyService.suppliers()
    assert len(rows) >= 18


def test_existing_sale_details():
    sale = SalesService.get_sale(1)
    assert sale is not None
    assert len(sale["items"]) >= 1


def test_existing_purchase_details():
    purchase = PurchaseService.get_purchase(1)
    assert purchase is not None


def test_party_master_has_full_crud_api():
    assert hasattr(PartyMasterService, "ensure_optional_fields")
    assert hasattr(PartyMasterService, "update_party")
