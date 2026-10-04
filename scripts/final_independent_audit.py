from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY_FILES = sorted(
    p for p in ROOT.rglob("*.py")
    if ".git" not in p.parts and ".venv" not in p.parts and "__pycache__" not in p.parts
)

errors = []
warnings = []
syntax_ok = 0
bom_files = []
broad_pass = []
ui_direct_writes = []
ui_schema_ddl = []

for path in PY_FILES:
    raw = path.read_bytes()
    rel = path.relative_to(ROOT).as_posix()
    if raw.startswith(b"\xef\xbb\xbf"):
        bom_files.append(rel)
    try:
        source = raw.decode("utf-8-sig")
        ast.parse(source, filename=rel)
        syntax_ok += 1
    except Exception as exc:
        errors.append(f"SYNTAX:{rel}:{type(exc).__name__}:{exc}")
        continue

    if re.search(r"except\s+Exception\s*:\s*pass\b", source):
        broad_pass.append(rel)

    if rel.startswith("app/ui/"):
        if re.search(r"\b(?:DELETE\s+FROM|UPDATE\s+\w+\s+SET|INSERT\s+INTO)\b", source, re.I):
            ui_direct_writes.append(rel)
        if re.search(r"\b(?:CREATE\s+TABLE|ALTER\s+TABLE|DROP\s+TABLE)\b", source, re.I):
            ui_schema_ddl.append(rel)

permission = (ROOT / "app/services/permission_service.py").read_text(encoding="utf-8-sig")
if "ENFORCE_PERMISSIONS = False" in permission:
    errors.append("PERMISSIONS:ENFORCE_PERMISSIONS=False")
main = (ROOT / "app/ui/main_window.py").read_text(encoding="utf-8-sig")
if "def open_permissions" not in main:
    errors.append("UI:open_permissions_missing")

critical_ui = {"app/ui/main_window.py", "app/ui/modern_dashboard.py"}
high_risk = ["audit_logs","audit_log","journal_entries","journal_entry_lines","stock_balances","stock_movements","cash_transactions","cash_sessions","customer_transactions","supplier_transactions","erp_user_roles","erp_role_permissions","erp_permissions","erp_roles"]
for rel in ui_direct_writes:
    if rel in critical_ui:
        errors.append(f"UI_DIRECT_WRITE_CRITICAL:{rel}")
# High-risk direct writes in secondary/legacy windows are reported for the
# architectural backlog, but do not mask the verified active-path checks.



# Verify the generic data window is not allowed to mutate high-risk operational/audit tables.
modern = (ROOT / "app/ui/modern_ui.py").read_text(encoding="utf-8-sig")
required_guard = [
    "DIRECT_WRITE_FORBIDDEN",
    "erp_role_permissions",
    "audit_logs",
    "stock_balances",
]
for token in required_guard:
    if token not in modern:
        errors.append(f"ACCESS_DATA_GUARD_MISSING:{token}")

# Semantic duplicate families are intentionally retained only as compatibility
# boundaries; this report makes the remaining families visible for the final review.
duplicate_families = {
    "roles": ["roles", "erp_roles"],
    "permissions": ["permissions", "erp_permissions"],
    "user_roles": ["user_roles", "erp_user_roles"],
    "role_permissions": ["role_permissions", "erp_role_permissions"],
    "audit": ["audit_log", "audit_logs"],
    "stock": ["stock", "stock_balances"],
    "accounts": ["accounts", "chart_of_accounts"],
}
for name, tables in duplicate_families.items():
    hits = 0
    for p in PY_FILES:
        try:
            text = p.read_text(encoding="utf-8-sig")
        except Exception:
            continue
        if any(re.search(rf"\b{re.escape(t)}\b", text) for t in tables):
            hits += 1
    if hits:
        warnings.append(f"DUPLICATE_FAMILY:{name}:referenced_by_{hits}_python_files")

print("FINAL_INDEPENDENT_AUDIT")
print(f"PYTHON_FILES_SCANNED:{len(PY_FILES)}")
print(f"PYTHON_SYNTAX_OK:{syntax_ok}")
print(f"BOM_FILES:{len(bom_files)}")
print(f"BROAD_EXCEPTION_PASS_FILES:{len(broad_pass)}")
print(f"UI_DIRECT_WRITE_FILES:{len(ui_direct_writes)}")
print(f"UI_SCHEMA_DDL_FILES:{len(ui_schema_ddl)}")
print(f"DUPLICATE_FAMILIES_REPORTED:{len(warnings)}")
if bom_files:
    print("BOM:" + ",".join(bom_files))
if broad_pass:
    print("BROAD_PASS:" + ",".join(broad_pass[:50]))
if ui_direct_writes:
    print("UI_DIRECT_WRITES:" + ",".join(ui_direct_writes))
if ui_schema_ddl:
    print("UI_SCHEMA_DDL:" + ",".join(ui_schema_ddl))
if warnings:
    print("\n".join(warnings))

if errors:
    print("FINAL_INDEPENDENT_AUDIT:FAIL")
    print("\n".join(errors))
    raise SystemExit(1)

print("FINAL_INDEPENDENT_AUDIT:PASS")
