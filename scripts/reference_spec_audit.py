from pathlib import Path
import ast
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "database" / "metadata" / "database_schema.json"
COMPAT = ROOT / "app" / "services" / "reference_compatibility_service.py"

required_files = [
    "app/ui/main_window.py", "app/ui/pos_window.py", "app/ui/access_data_window.py",
    "app/ui/permissions_window.py", "app/ui/expense_window.py", "app/ui/analytics_window.py",
    "app/ui/universal_search_window.py", "app/ui/reports_window.py", "app/ui/stocktake_window.py",
    "app/ui/purchase_invoice_window.py", "app/ui/sales_invoice_window.py",
    "app/ui/purchase_workflow_window.py", "app/ui/treasury_operations_window.py",
    "app/ui/backup_window.py", "app/ui/settings_window.py",
    "app/services/reference_compatibility_service.py", "app/services/expense_service.py",
    "app/services/accounting_reports_service.py", "app/services/sales_return_service.py",
    "app/services/purchase_return_service.py", "app/services/inventory_service.py",
    "app/services/pos_service.py", "app/services/purchase_service.py",
    "app/services/universal_search_service.py", "app/database/schema_bootstrap.py",
]

required_tokens = {
    "app/ui/main_window.py": ["LoginDialog", "QComboBox", "AccessDataWindow", "stock_balances", "warehouse_zones", "employee_attendance", "_close_other_windows"],
    "app/database/schema_bootstrap.py": ["database_schema.json", "CREATE TABLE IF NOT EXISTS"],
    "app/services/sales_return_service.py": ["sale_returns", "sale_return_items", "stock_balances"],
    "app/services/purchase_return_service.py": ["purchase_returns", "purchase_return_items", "stock_balances"],
    "app/ui/pos_window.py": ["QShortcut", "self.search.textChanged", "QTableWidget(1, 10)", "self._focus_product_cell", "payments", "hold_sale"],
    "app/ui/access_data_window.py": ["AccessDataWindow", "RecordDialog", "app.ui.modern_ui"],
    "app/ui/modern_ui.py": ["textChanged", "QTableWidget", "doubleClicked", "LIMIT", "export_data", "print_table"],
    "app/ui/universal_search_window.py": ["UniversalSearchWindow", "app.ui.modern_ui_runtime"],
    "app/ui/modern_ui_runtime.py": ["textChanged", "UniversalSearchService"],
    "app/ui/reports_window.py": ["QDateEdit", "to_excel", "to_pdf", "sales_day", "low_stock", "journal", "income", "cashflow"],
    "app/ui/backup_window.py": ["إنشاء نسخة الآن", "استعادة النسخة المحددة"],
    "app/ui/sales_invoice_window.py": ["QTabWidget", "مرتجع جزئي / كامل", "طباعة الفاتورة"],
    "app/ui/purchase_workflow_window.py": ["PurchaseWorkflowWindow", "app.ui.modern_purchase_workflow"],
    "app/ui/modern_purchase_workflow.py": ["طلب شراء جديد", "اعتماد الطلب", "استلام أمر"],
    "app/ui/treasury_operations_window.py": ["سند قبض", "سند صرف", "فتح وردية", "إغلاق وردية"],
    "app/ui/stocktake_window.py": ["inventory.stocktake", "inventory.adjust", "stocktake_items", "STOCKTAKE_APPROVED"],
    "app/ui/purchase_invoice_window.py": ["QTabWidget", "المحاسبة", "المستندات", "المرتجعات"],
    "app/services/universal_search_service.py": ["cash_receipts", "cash_payments", "documents", "normalize"],
    "app/ui/settings_window.py": ["المنشأة", "النظام", "المبيعات", "المخزون", "الطباعة", "الأمان"],
    "app/services/accounting_reports_service.py": ["income_statement", "balance_sheet", "cash_flow_summary"],
    "app/services/pos_service.py": ["stock_balances", "sale_payments", "AccountingService"],
    "app/services/purchase_service.py": ["stock_balances", "purchase_invoice_items", "AccountingService"],
}

errors = []
for path in required_files:
    p = ROOT / path
    if not p.exists():
        errors.append(f"FILE_MISSING:{path}")
        continue
    try:
        source = p.read_text(encoding="utf-8-sig")
        ast.parse(source, filename=path)
    except Exception as exc:
        errors.append(f"SYNTAX:{path}:{exc}")
        continue
    for token in required_tokens.get(path, []):
        if token not in source:
            errors.append(f"TOKEN_MISSING:{path}:{token}")

main_text = (ROOT / "app/ui/main_window.py").read_text(encoding="utf-8-sig")
for forbidden in ["HealthWindow", "صحة النظام", '("العقود"']:
    if forbidden in main_text:
        errors.append(f"FORBIDDEN_VISIBLE_MODULE:{forbidden}")
for pattern in [r"25,000\s*=", r"25000\s*=", r"1000000\s*=", r"30000\s*="]:
    if re.search(pattern, main_text):
        errors.append(f"STATIC_DEMO_NUMBER:{pattern}")

# مخطط JSON هو المرجع الأساسي. بعض الكيانات المطلوبة في الـPDF تُنشأ
# في طبقة التوافق وقت التشغيل حتى لا نضطر لتخزين قاعدة SQLite داخل Git.
try:
    spec = json.loads(SCHEMA.read_text(encoding="utf-8"))
    tables = set((spec.get("tables") or {}).keys())
    compat_text = COMPAT.read_text(encoding="utf-8-sig") if COMPAT.exists() else ""
    runtime_tables = {"expenses"} if re.search(r"CREATE TABLE IF NOT EXISTS\s+expenses\b", compat_text, re.I) else set()
    table_groups = {
        "companies": {"companies"}, "branches": {"branches"}, "users": {"users"},
        "roles": {"roles"}, "permissions": {"permissions"}, "user_roles": {"user_roles"},
        "role_permissions": {"role_permissions"}, "products": {"products"},
        "product_barcodes": {"product_barcodes"}, "categories": {"categories", "product_categories"},
        "units": {"units"}, "warehouses": {"warehouses"},
        "warehouse_locations": {"warehouse_locations", "warehouse_zones", "warehouse_bins"},
        "customers": {"customers"}, "suppliers": {"suppliers"}, "sales": {"sales"},
        "sale_items": {"sale_items"}, "purchases": {"purchases", "purchase_invoices"},
        "purchase_items": {"purchase_items", "purchase_invoice_items"},
        "returns": {"returns", "sales_returns", "purchase_returns"},
        "inventory_transactions": {"inventory_transactions", "stock_movements"},
        "stocktakes": {"stocktakes"}, "cashboxes": {"cashboxes", "cash_registers"},
        "cash_transactions": {"cash_transactions"}, "bank_accounts": {"bank_accounts"},
        "bank_transactions": {"bank_transactions"}, "expenses": {"expenses"},
        "accounts": {"accounts", "chart_of_accounts"}, "journal_entries": {"journal_entries"},
        "journal_entry_lines": {"journal_entry_lines", "journalentrylines"},
        "taxes": {"taxes", "tax_rates"}, "documents": {"documents"},
        "document_sequences": {"document_sequences"}, "notifications": {"notifications"},
        "audit_logs": {"audit_logs", "audit_log"}, "system_settings": {"system_settings", "settings"},
        "schema_versions": {"schema_versions"},
    }
    for canonical, aliases in table_groups.items():
        if not ((tables | runtime_tables) & aliases):
            errors.append(f"TABLE_GROUP_MISSING:{canonical}:{sorted(aliases)}")
except Exception as exc:
    errors.append(f"SCHEMA_AUDIT_ERROR:{exc}")

print("REFERENCE_FILES:", len(required_files))
print("REFERENCE_TOKEN_CHECKS:", sum(len(v) for v in required_tokens.values()))
print("REFERENCE_DATABASE_CHECKS: 35 semantic table groups")
if errors:
    print("REFERENCE_SPEC_AUDIT: FAIL")
    print("\n".join(errors))
    sys.exit(1)
print("REFERENCE_SPEC_AUDIT: PASS")
