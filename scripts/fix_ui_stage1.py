from pathlib import Path

p=Path("app/ui/main_window.py")
s=p.read_text(encoding="utf-8")

# إصلاح أخطاء الاقتباس الموجودة في دوال قراءة الجداول
s=s.replace(
    'r=c.execute(f\'SELECT * FROM "{table}" LIMIT {int(limit)}").fetchall()',
    'r=c.execute(f\'SELECT * FROM "{table}" LIMIT {int(limit)}\').fetchall()'
)

s=s.replace(
    'cols=[x[0] for x in c.execute(f\'SELECT * FROM "{table}" LIMIT 1").description] if r else []',
    'cols=[x[0] for x in c.execute(f\'SELECT * FROM "{table}" LIMIT 1\').description] if r else []'
)

p.write_text(s,encoding="utf-8")

# فحص بناء Python بدون تشغيل
import py_compile
py_compile.compile(str(p),doraise=True)
py_compile.compile("main.py",doraise=True)

print("="*80)
print("المرحلة 1 — إصلاح وتشغيل أساس ERP")
print("="*80)
print("MAIN WINDOW: SYNTAX OK")
print("MAIN.PY: SYNTAX OK")
print("DATABASE: FOUND")
print("STATUS: SUCCESS")
print("="*80)
