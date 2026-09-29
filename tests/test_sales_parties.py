
from app.services.sales_service import SalesService,PurchaseService
from app.services.party_service import PartyService

def test_sales_list():
    rows=SalesService.list_sales()
    assert len(rows)>=4

def test_purchase_list():
    rows=PurchaseService.list_purchases()
    assert len(rows)>=6

def test_customers():
    rows=PartyService.customers()
    assert len(rows)>=28

def test_suppliers():
    rows=PartyService.suppliers()
    assert len(rows)>=18

def test_existing_sale_details():
    sale=SalesService.get_sale(1)
    assert sale is not None
    assert len(sale["items"])>=1

def test_existing_purchase_details():
    purchase=PurchaseService.get_purchase(1)
    assert purchase is not None
