from pathlib import Path
import ast

ROOT = Path.cwd()
MAIN = ROOT / "app" / "ui" / "main_window.py"

print("=" * 80)
print("POS UI STRUCTURE INSPECTION")
print("=" * 80)

source = MAIN.read_text(encoding="utf-8")
tree = ast.parse(source)

# البحث عن كل الكلاسات والدوال المتعلقة بـ POS
for cls in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
    name = cls.name
    methods = [
        n.name for n in cls.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]

    relevant = (
        "pos" in name.lower()
        or any(
            any(x in m.lower() for x in [
                "pos", "sale", "search", "product",
                "cart", "invoice", "barcode"
            ])
            for m in methods
        )
    )

    if relevant:
        print()
        print("CLASS:", name)
        print("METHODS:")

        for m in methods:
            if any(x in m.lower() for x in [
                "pos", "sale", "search", "product",
                "cart", "invoice", "barcode"
            ]):
                print("  -", m)

print()
print("-" * 80)
print("POS RELATED TEXT LOCATIONS")
print("-" * 80)

keywords = [
    "POS",
    "pos",
    "بحث",
    "search",
    "barcode",
    "باركود",
    "sale",
    "بيع",
    "product",
    "منتج",
    "cart",
    "سلة",
    "invoice",
    "فاتورة"
]

lines = source.splitlines()

shown = set()

for i, line in enumerate(lines, 1):
    low = line.lower()

    if any(k.lower() in low for k in keywords):
        # منع طباعة نفس السطر أكثر من مرة
        if i not in shown:
            shown.add(i)
            print(f"{i:5}: {line[:220]}")

print()
print("=" * 80)
print("STATUS: INSPECTION COMPLETE")
print("=" * 80)
