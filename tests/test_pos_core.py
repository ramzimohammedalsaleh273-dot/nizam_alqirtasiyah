from app.services.inventory_service import InventoryService
from app.services.pos_search_service import POSProductSearch
from app.services.tax_service import TaxService


def test_product_search():
    products = InventoryService.search_products("دفتر")
    assert isinstance(products, list)


def test_product_exists():
    product = InventoryService.get_product(1)
    assert product is not None
    assert product["id"] == 1


def test_stock_available():
    quantity = InventoryService.available_quantity(1, 1)
    assert quantity >= 0


def test_pos_search_has_operational_fields():
    rows = POSProductSearch().search("دفتر")
    assert isinstance(rows, list)
    if rows:
        assert {"id", "sku", "name_ar", "sale_price", "available_quantity", "barcode"} <= set(rows[0])


def test_tax_calculation():
    result = TaxService.calculate("100.00", rate="15")
    assert result["base"] == 100.0
    assert result["tax"] == 15.0
    assert result["total"] == 115.0
