from __future__ import annotations

import importlib
import inspect
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QWidget

ROOT = Path(__file__).resolve().parents[1]
UI_ROOT = ROOT / "app" / "ui"


def _required_args(cls) -> list[str]:
    try:
        sig = inspect.signature(cls.__init__)
    except (TypeError, ValueError):
        return []
    required = []
    for p in list(sig.parameters.values())[1:]:
        if p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue
        if p.default is inspect.Parameter.empty and p.name != "parent":
            required.append(p.name)
    return required


def main() -> int:
    app = QApplication.instance() or QApplication([])
    modules = []
    import_errors = []
    for path in sorted(UI_ROOT.rglob("*.py")):
        if path.name == "__init__.py" or path.name == "theme.py":
            continue
        rel = path.relative_to(ROOT).with_suffix("")
        module_name = ".".join(rel.parts)
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

    failures = []
    skipped = []
    passed = 0
    for module_name, name, cls in classes:
        required = _required_args(cls)
        if required:
            skipped.append(f"{module_name}.{name}: required arguments={required}")
            continue
        widget = None
        try:
            widget = cls()
            widget.show()
            app.processEvents()
            widget.close()
            widget.deleteLater()
            passed += 1
        except Exception as exc:
            failures.append(f"{module_name}.{name}: {type(exc).__name__}: {exc}")
            if widget is not None:
                try:
                    widget.close()
                except Exception:
                    pass

    app.processEvents()
    print("=" * 80)
    print("فحص واجهات ونوافذ نظام القرطاسية")
    print("=" * 80)
    print(f"ملفات واجهة تم استيرادها: {len(modules)}")
    print(f"أخطاء الاستيراد: {len(import_errors)}")
    print(f"أصناف QWidget المكتشفة: {len(classes)}")
    print(f"نوافذ/عناصر قابلة للإنشاء تلقائيًا: {passed}")
    print(f"أصناف تحتاج معاملات إلزامية: {len(skipped)}")
    print(f"فشل الإنشاء أو العرض: {len(failures)}")
    if import_errors:
        print("\nأخطاء الاستيراد:")
        print("\n".join(import_errors))
    if failures:
        print("\nأخطاء النوافذ:")
        print("\n".join(failures))
    if skipped:
        print("\nالنوافذ ذات المعاملات الإلزامية:")
        print("\n".join(skipped))
    print("=" * 80)
    if import_errors or failures:
        print("UI WINDOWS ACCEPTANCE: FAIL")
        return 1
    print("UI WINDOWS ACCEPTANCE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
