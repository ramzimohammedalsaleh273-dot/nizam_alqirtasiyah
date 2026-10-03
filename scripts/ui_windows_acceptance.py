from __future__ import annotations

import importlib
import inspect
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication, QWidget

UI_ROOT = ROOT / "app" / "ui"

SAFE_ARGS = {
    "table_name": "products",
    "title": "فحص الواجهة",
    "fields": [],
    "sections": [],
    "product_id": 1,
    "party_id": 1,
    "total": 10,
    "data": {},
    "session_id": 1,
}


def _constructor_arguments(cls):
    try:
        sig = inspect.signature(cls.__init__)
    except (TypeError, ValueError):
        return None, []
    args = {}
    missing = []
    for p in list(sig.parameters.values())[1:]:
        if p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD) or p.name == "parent":
            continue
        if p.default is not inspect.Parameter.empty:
            continue
        if p.name in SAFE_ARGS:
            args[p.name] = SAFE_ARGS[p.name]
        else:
            missing.append(p.name)
    return args, missing


def main() -> int:
    app = QApplication.instance() or QApplication([])
    modules, import_errors = [], []
    for path in sorted(UI_ROOT.rglob("*.py")):
        if path.name in {"__init__.py", "theme.py"}:
            continue
        module_name = ".".join(path.relative_to(ROOT).with_suffix("").parts)
        try:
            modules.append(importlib.import_module(module_name))
        except Exception as exc:
            import_errors.append(f"{module_name}: {type(exc).__name__}: {exc}")

    classes = []
    for module in modules:
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if obj.__module__ != module.__name__:
                continue
            try:
                if issubclass(obj, QWidget):
                    classes.append((module.__name__, name, obj))
            except TypeError:
                pass

    failures, skipped = [], []
    passed = 0
    for module_name, name, cls in classes:
        args, missing = _constructor_arguments(cls)
        if missing:
            skipped.append(f"{module_name}.{name}: required arguments={missing}")
            continue
        widget = None
        try:
            widget = cls(**args)
            widget.show(); app.processEvents(); widget.close(); widget.deleteLater(); passed += 1
        except Exception as exc:
            failures.append(f"{module_name}.{name}: {type(exc).__name__}: {exc}")
            if widget is not None:
                try: widget.close()
                except Exception: pass

    app.processEvents()
    print("=" * 80)
    print("فحص واجهات ونوافذ نظام القرطاسية")
    print("=" * 80)
    print(f"ملفات واجهة تم استيرادها: {len(modules)}")
    print(f"أخطاء الاستيراد: {len(import_errors)}")
    print(f"أصناف QWidget المكتشفة: {len(classes)}")
    print(f"نوافذ/عناصر تم إنشاؤها وعرضها: {passed}")
    print(f"أصناف لا يمكن تجهيزها بالبيانات الآمنة: {len(skipped)}")
    print(f"فشل الإنشاء أو العرض: {len(failures)}")
    if import_errors:
        print("\nأخطاء الاستيراد:\n" + "\n".join(import_errors))
    if failures:
        print("\nأخطاء النوافذ:\n" + "\n".join(failures))
    if skipped:
        print("\nنوافذ تحتاج معاملات غير معروفة:\n" + "\n".join(skipped))
    print("=" * 80)
    if import_errors or failures or skipped:
        print("UI WINDOWS ACCEPTANCE: FAIL")
        return 1
    print("UI WINDOWS ACCEPTANCE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
