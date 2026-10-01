from pathlib import Path
import ast, sys

ROOT=Path(__file__).resolve().parents[1]
required_files=[
"app/ui/main_window.py","app/ui/pos_window.py","app/ui/access_data_window.py","app/ui/permissions_window.py",
"app/ui/expense_window.py","app/ui/analytics_window.py","app/ui/universal_search_window.py",
"app/ui/reports_window.py","app/ui/stocktake_window.py","app/ui/purchase_invoice_window.py","app/services/reference_compatibility_service.py","app/services/expense_service.py","app/services/accounting_reports_service.py",
"app/database/schema_bootstrap.py","app/services/sales_return_service.py","app/services/purchase_return_service.py",
]
required_tokens={
"app/ui/main_window.py":["QTimer","AccessDataWindow","ReferenceCompatibilityService","show_dashboard","ensure_reference_schema"],
"app/database/schema_bootstrap.py":["database_schema.json","CREATE TABLE IF NOT EXISTS"],
"app/services/sales_return_service.py":["sale_returns","sale_return_items","stock_balances"],
"app/services/purchase_return_service.py":["purchase_returns","purchase_return_items","stock_balances"],
"app/ui/pos_window.py":["QShortcut","self.search.textChanged","QTableWidget(1, 10)","self._focus_product_cell"],
"app/ui/access_data_window.py":["textChanged","QTableWidget","cellDoubleClicked","QMenu","LIMIT"],
"app/ui/universal_search_window.py":["textChanged","UniversalSearchService"],
"app/ui/reports_window.py":["QDateEdit","to_excel","to_pdf","sales_day","low_stock","journal","income","cashflow"],
"app/ui/main_window.py":["LoginDialog","QComboBox","AccessDataWindow","stock_balances","warehouse_zones","employee_attendance"],
"app/ui/backup_window.py":["إنشاء نسخة الآن","استعادة النسخة المحددة"],
"app/ui/sales_invoice_window.py":["QTabWidget","مرتجع جزئي / كامل","طباعة الفاتورة"],
"app/ui/purchase_workflow_window.py":["طلب شراء جديد","اعتماد الطلب","استلام أمر"],
"app/ui/treasury_operations_window.py":["سند قبض","سند صرف","فتح وردية","إغلاق وردية"],
"app/services/inventory_service.py":["stock_balances","product_barcodes"],
"app/ui/stocktake_window.py":["inventory.stocktake","inventory.adjust","stocktake_items","STOCKTAKE_APPROVED"],
"app/ui/purchase_invoice_window.py":["QTabWidget","المحاسبة","المستندات","المرتجعات"],
"app/services/universal_search_service.py":["cash_receipts","cash_payments","documents","normalize"],
"app/ui/settings_window.py":["المنشأة","النظام","المبيعات","المخزون","الطباعة","الأمان"],
"app/services/accounting_reports_service.py":["income_statement","balance_sheet","cash_flow_summary"],
"app/services/pos_service.py":["stock_balances","sale_payments","AccountingService"],
"app/services/purchase_service.py":["stock_balances","purchase_invoice_items","AccountingService"],
}
errors=[]
for p in required_files:
    if not (ROOT/p).exists(): errors.append(f"FILE_MISSING:{p}")
for p,tokens in required_tokens.items():
    text=(ROOT/p).read_text(encoding="utf-8-sig")
    for token in tokens:
        if token not in text: errors.append(f"TOKEN_MISSING:{p}:{token}")
for p in required_files:
    if p.endswith(".py"):
        try: ast.parse((ROOT/p).read_text(encoding="utf-8-sig"),filename=p)
        except Exception as e: errors.append(f"SYNTAX:{p}:{e}")
print("REFERENCE_FILES:",len(required_files))
print("REFERENCE_TOKEN_CHECKS:",sum(len(v) for v in required_tokens.values()))
if errors:
    print("REFERENCE_SPEC_AUDIT: FAIL")
    print("\n".join(errors))
    sys.exit(1)
print("REFERENCE_SPEC_AUDIT: PASS")


# منع عودة الوحدات الزائدة التي لا تظهر في المواصفة المرجعية النهائية.
main_text=(ROOT/"app/ui/main_window.py").read_text(encoding="utf-8-sig")
for forbidden in ["HealthWindow", "صحة النظام", '("الأصول"', '("العقود"']:
    if forbidden in main_text:
        errors.append(f"FORBIDDEN_VISIBLE_MODULE:{forbidden}")
