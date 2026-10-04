from __future__ import annotations
import importlib,inspect,os,sys
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication,QWidget,QMessageBox
UI_ROOT=ROOT/'app'/'ui'
SAFE_ARGS={'table_name':'products','title':'فحص الواجهة','fields':[],'sections':[],'product_id':1,'party_id':1,'total':10,'data':{},'session_id':1,'mode':'view','kind':'sale','document_id':1,'party_type':'customer','sale_id':1,'cart':[],'payments':[]}
BLOCKED=[]
SKIP_MODULES={'app.ui.final_ui'}

def close_blocking_dialogs():
    app=QApplication.instance()
    if not app:return
    for w in app.topLevelWidgets():
        if isinstance(w,QMessageBox) and w.isVisible():
            BLOCKED.append(f'{type(w).__name__}: {w.windowTitle()} — {w.text()}')
            w.done(0)

def args_for(cls):
    try:sig=inspect.signature(cls.__init__)
    except:return None,[]
    args={};missing=[]
    for p in list(sig.parameters.values())[1:]:
        if p.kind in (inspect.Parameter.VAR_POSITIONAL,inspect.Parameter.VAR_KEYWORD) or p.name=='parent' or p.default is not inspect.Parameter.empty:continue
        if p.name in SAFE_ARGS:args[p.name]=SAFE_ARGS[p.name]
        else:missing.append(p.name)
    return args,missing

def main():
    app=QApplication.instance() or QApplication([]);app.setQuitOnLastWindowClosed(False);timer=QTimer();timer.timeout.connect(close_blocking_dialogs);timer.start(100)
    modules=[];imports=[]
    for path in sorted(UI_ROOT.rglob('*.py')):
        if path.name in {'__init__.py','theme.py'}:continue
        name='.'.join(path.relative_to(ROOT).with_suffix('').parts)
        if name in SKIP_MODULES:continue
        try:modules.append(importlib.import_module(name))
        except Exception as e:imports.append(f'{name}: {type(e).__name__}: {e}')
    classes=[]
    for m in modules:
        for name,obj in inspect.getmembers(m,inspect.isclass):
            if obj.__module__!=m.__name__:continue
            try:
                if issubclass(obj,QWidget):classes.append((m.__name__,name,obj))
            except TypeError:pass
    failures=[];skipped=[];passed=0
    for module,name,cls in classes:
        args,missing=args_for(cls)
        if missing:skipped.append(f'{module}.{name}: {missing}');continue
        try:
            w=cls(**args);w.show();app.processEvents();close_blocking_dialogs();w.close();w.deleteLater();passed+=1
        except Exception as e:failures.append(f'{module}.{name}: {type(e).__name__}: {e}')
        app.processEvents()
    timer.stop();app.processEvents();print('='*80);print('فحص واجهات ونوافذ نظام القرطاسية');print(f'ملفات الواجهة الفعالة: {len(modules)}');print(f'أخطاء الاستيراد: {len(imports)}');print(f'أصناف QWidget الفعالة: {len(classes)}');print(f'تم الإنشاء والعرض: {passed}');print(f'تحتاج معاملات غير معروفة: {len(skipped)}');print(f'أخطاء الإنشاء: {len(failures)}');print(f'نوافذ خطأ أغلقت أثناء الفحص: {len(BLOCKED)}')
    if imports:print('\n'.join(imports))
    if failures:print('\n'.join(failures))
    if skipped:print('\n'.join(skipped))
    if BLOCKED:print('\n'.join(BLOCKED))
    print('='*80)
    if imports or failures or skipped or BLOCKED:return 1
    print('UI WINDOWS ACCEPTANCE: PASS');return 0
if __name__=='__main__':raise SystemExit(main())
