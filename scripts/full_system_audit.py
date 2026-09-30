from pathlib import Path
import sqlite3
import subprocess
import sys
import ast
import re
import json
from datetime import datetime

ROOT = Path.cwd()
DB = ROOT / "database" / "nizam_alqirtasiyah.db"
OUT = ROOT / "FULL_SYSTEM_AUDIT.md"

lines = []

def add(x=""):
    lines.append(str(x))

def run(cmd):
    try:
        p = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as e:
        return 999, str(e)

add("# نظام القرطاسية — التدقيق الشامل للمشروع")
add("")
add(f"تاريخ التدقيق: {datetime.now().isoformat()}")
add(f"المسار: `{ROOT}`")
add("")
add("## 1. حالة Git")
add("```text")
rc, out = run(["git", "status", "--short", "--branch"])
add(out)
rc, out = run(["git", "log", "-8", "--oneline", "--decorate"])
add(out)
add("```")

add("## 2. شجرة المشروع")
add("```text")
all_files = sorted(
    p.relative_to(ROOT).as_posix()
    for p in ROOT.rglob("*")
    if p.is_file()
    and ".git" not in p.parts
    and ".venv" not in p.parts
    and "__pycache__" not in p.parts
)
for p in all_files:
    add(p)
add("```")

py_files = [ROOT / p for p in all_files if p.endswith(".py")]

add("")
add("## 3. إحصاءات المشروع")
add(f"- إجمالي الملفات: {len(all_files)}")
add(f"- ملفات Python: {len(py_files)}")
add(f"- ملفات الاختبارات: {len([p for p in all_files if 'test' in p.lower()])}")
add(f"- ملفات الواجهات: {len([p for p in all_files if '/ui/' in p.lower() or p.startswith('app/ui/')])}")
add(f"- ملفات الخدمات: {len([p for p in all_files if '/services/' in p.lower()])}")
add("")

# Python syntax/import-oriented audit
add("## 4. فحص صياغة Python")
syntax_errors = []
for p in py_files:
    try:
        ast.parse(p.read_text(encoding="utf-8", errors="replace"), filename=str(p))
    except Exception as e:
        syntax_errors.append((p.relative_to(ROOT).as_posix(), repr(e)))

if syntax_errors:
    add("### أخطاء الصياغة")
    for p, e in syntax_errors:
        add(f"- `{p}`: {e}")
else:
    add("PASS: لم يتم العثور على أخطاء Syntax في ملفات Python.")

# TODO/FIXME/pass/NotImplemented
add("")
add("## 5. مؤشرات النقص البرمجي")
patterns = {
    "TODO": re.compile(r"\bTODO\b", re.I),
    "FIXME": re.compile(r"\bFIXME\b", re.I),
    "NotImplemented": re.compile(r"NotImplemented|NotImplementedError", re.I),
    "pass_only": re.compile(r"^\s*pass\s*(?:#.*)?$", re.M),
}

for name, pat in patterns.items():
    hits = []
    for p in py_files:
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
        except:
            continue
        if pat.search(txt):
            hits.append(p.relative_to(ROOT).as_posix())
    add(f"### {name}")
    if hits:
        for h in hits:
            add(f"- `{h}`")
    else:
        add("- لا توجد نتائج.")

# UI inventory
add("")
add("## 6. واجهات المستخدم")
ui_files = sorted(
    p for p in all_files
    if p.startswith("app/ui/") and p.endswith(".py")
)
for p in ui_files:
    add(f"- `{p}`")

# Services inventory
add("")
add("## 7. الخدمات")
service_files = sorted(
    p for p in all_files
    if p.startswith("app/services/") and p.endswith(".py")
)
for p in service_files:
    add(f"- `{p}`")

# Database
add("")
add("## 8. قاعدة البيانات")

if not DB.exists():
    add("FAIL: قاعدة البيانات غير موجودة.")
else:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row

    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    fk = con.execute("PRAGMA foreign_key_check").fetchall()

    add(f"- المسار: `{DB}`")
    add(f"- الحجم بالبايت: {DB.stat().st_size}")
    add(f"- SQLite integrity_check: `{integrity}`")
    add(f"- foreign_key_check violations: `{len(fk)}`")

    if fk:
        add("### مخالفات Foreign Keys")
        for row in fk[:500]:
            add(f"- {tuple(row)}")

    tables = [
        r["name"]
        for r in con.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type='table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
    ]

    add("")
    add(f"### عدد الجداول: {len(tables)}")

    for table in tables:
        add("")
        add(f"### TABLE: `{table}`")

        cols = con.execute(
            f'PRAGMA table_info("{table.replace(chr(34), chr(34)*2)}")'
        ).fetchall()

        add("#### الأعمدة")
        add("| cid | name | type | notnull | default | pk |")
        add("|---:|---|---|---:|---|---:|")
        for c in cols:
            add(
                f"| {c['cid']} | `{c['name']}` | `{c['type']}` | "
                f"{c['notnull']} | `{c['dflt_value']}` | {c['pk']} |"
            )

        fks = con.execute(
            f'PRAGMA foreign_key_list("{table.replace(chr(34), chr(34)*2)}")'
        ).fetchall()

        add("#### العلاقات / Foreign Keys")
        if fks:
            for f in fks:
                add(
                    f"- `{f['from']}` → `{f['table']}.{f['to']}` "
                    f"(on_update={f['on_update']}, on_delete={f['on_delete']})"
                )
        else:
            add("- لا توجد Foreign Keys.")

        indexes = con.execute(
            f'PRAGMA index_list("{table.replace(chr(34), chr(34)*2)}")'
        ).fetchall()

        add("#### الفهارس")
        if indexes:
            for idx in indexes:
                idx_name = idx["name"]
                idx_cols = con.execute(
                    f'PRAGMA index_info("{idx_name.replace(chr(34), chr(34)*2)}")'
                ).fetchall()
                names = ", ".join(str(x["name"]) for x in idx_cols)
                add(
                    f"- `{idx_name}` | unique={idx['unique']} | "
                    f"columns=({names})"
                )
        else:
            add("- لا توجد فهارس.")

        try:
            count = con.execute(
                f'SELECT COUNT(*) FROM "{table.replace(chr(34), chr(34)*2)}"'
            ).fetchone()[0]
            add(f"#### عدد السجلات: **{count}**")
        except Exception as e:
            add(f"#### عدد السجلات: ERROR — {e}")

    # Settings
    add("")
    add("## 9. إعدادات النظام")
    try:
        rows = con.execute(
            "SELECT key, value FROM system_settings ORDER BY key"
        ).fetchall()
        if rows:
            add("| المفتاح | القيمة |")
            add("|---|---|")
            for r in rows:
                value = "" if r["value"] is None else str(r["value"])
                value = value.replace("|", "\\|")
                add(f"| `{r['key']}` | `{value}` |")
        else:
            add("لا توجد إعدادات.")
    except Exception as e:
        add(f"تعذر قراءة system_settings: {e}")

    con.close()

# Search important architecture terms in source
add("")
add("## 10. تغطية المكونات المطلوبة")
required_terms = [
    "customers",
    "suppliers",
    "products",
    "product_barcodes",
    "warehouses",
    "stock",
    "stock_movements",
    "stocktakes",
    "sales",
    "sale_items",
    "sale_payments",
    "returns",
    "purchase_orders",
    "purchase_invoices",
    "purchase_returns",
    "cash_registers",
    "cash_sessions",
    "treasury_accounts",
    "bank_accounts",
    "accounts",
    "journal_entries",
    "journal_entry_lines",
    "fiscal_periods",
    "tax_invoices",
    "zatca",
    "printing",
    "employees",
    "attendance",
    "leaves",
    "payroll",
    "assets",
    "contracts",
    "reports",
    "analytics",
    "notifications",
    "sync_queue",
    "integrations",
    "branches",
    "workflows",
    "approval",
    "backup",
    "restore",
    "version",
    "search",
    "audit",
    "permissions",
    "authentication",
]

source_text = ""
for p in py_files:
    try:
        source_text += "\n" + p.read_text(encoding="utf-8", errors="replace").lower()
    except:
        pass

for term in required_terms:
    found = term.lower() in source_text
    add(f"- {'PASS' if found else 'REVIEW'} `{term}`")

# Focused POS inspection
add("")
add("## 11. تدقيق نقطة البيع")
pos_path = ROOT / "app" / "ui" / "pos_window.py"
if pos_path.exists():
    txt = pos_path.read_text(encoding="utf-8", errors="replace")
    checks = {
        "بحث المنتجات": "search_products",
        "Enter": "returnPressed",
        "اختيار نتائج متعددة": "QDialog",
        "الضريبة": "TaxService",
        "العميل": "PartyService",
        "الدفع المختلط": "payments",
        "الفواتير المعلقة": "POSHoldService",
    }
    for name, term in checks.items():
        add(f"- {'PASS' if term in txt else 'REVIEW'} {name}: `{term}`")
else:
    add("FAIL: pos_window.py غير موجود.")

# Parties inspection
add("")
add("## 12. تدقيق العملاء والموردين")
party_path = ROOT / "app" / "ui" / "parties_window.py"
if party_path.exists():
    txt = party_path.read_text(encoding="utf-8", errors="replace")
    for term in ["QInputDialog", "create_customer", "create_supplier"]:
        add(f"- {'FOUND' if term in txt else 'MISSING'} `{term}`")
else:
    add("FAIL: parties_window.py غير موجود.")

# Tests
add("")
add("## 13. الاختبارات")
test_files = [
    p for p in all_files
    if p.startswith("tests/") and p.endswith(".py")
]
for p in test_files:
    add(f"- `{p}`")

# Run pytest if available, but don't modify DB
add("")
add("## 14. نتيجة pytest")
rc, out = run([
    str(ROOT / ".venv" / "Scripts" / "python.exe"),
    "-m", "pytest", "-q"
])
add("```text")
add(out[-20000:])
add("```")
add(f"Exit code: {rc}")

# Acceptance if available
accept = ROOT / "scripts" / "run_enterprise_acceptance.py"
if accept.exists():
    add("")
    add("## 15. اختبار القبول المؤسسي")
    rc, out = run([
        str(ROOT / ".venv" / "Scripts" / "python.exe"),
        str(accept)
    ])
    add("```text")
    add(out[-12000:])
    add("```")
    add(f"Exit code: {rc}")

add("")
add("## 16. ملفات المراحل")
stage_files = sorted(
    p for p in all_files
    if re.search(r"(^|/)stage_\d+\.py$", p)
    or "complete_remaining_stages.py" in p
)
for p in stage_files:
    add(f"- `{p}`")

add("")
add("## 17. الملفات المرشحة للمراجعة اليدوية")
review_candidates = []
for p in py_files:
    try:
        txt = p.read_text(encoding="utf-8", errors="replace")
        score = 0
        if "pass" in txt:
            score += 1
        if "TODO" in txt or "FIXME" in txt:
            score += 3
        if "NotImplemented" in txt:
            score += 5
        if "except Exception:" in txt:
            score += 1
        if score >= 2:
            review_candidates.append((score, p.relative_to(ROOT).as_posix()))
    except:
        pass

for score, p in sorted(review_candidates, reverse=True):
    add(f"- درجة مراجعة {score}: `{p}`")

add("")
add("## 18. ملاحظات التدقيق")
add("")
add("هذا الملف هو تقرير تشخيصي وليس إعلانًا بأن النظام مكتمل.")
add("سيتم استخدامه لمراجعة الفجوات بين المواصفة المطلوبة والتنفيذ الفعلي.")
add("لا يتم حذف قاعدة البيانات أو إنشاء قاعدة بديلة بواسطة هذا التدقيق.")
add("")
add("## END OF AUDIT")

OUT.write_text("\n".join(lines), encoding="utf-8")

print("AUDIT CREATED:")
print(OUT)
print(f"FILES: {len(all_files)}")
print(f"PYTHON FILES: {len(py_files)}")
print(f"SYNTAX ERRORS: {len(syntax_errors)}")
if DB.exists():
    print("DATABASE: FOUND")
else:
    print("DATABASE: MISSING")
