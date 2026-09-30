from app.services.sales_invoice_service import SalesInvoiceService


def test_sales_invoice_service_has_lookup():
    assert callable(SalesInvoiceService.find_by_number)
    assert callable(SalesInvoiceService.returnable_items)
