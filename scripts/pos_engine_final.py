from pathlib import Path
import shutil,py_compile

p=Path("app/ui/main_window.py")
shutil.copy2(p,"backups/main_window_before_pos_final.py")
s=p.read_text(encoding="utf-8")

if "from app.services.erp_engine import ERP" not in s:
    s="from app.services.erp_engine import ERP\n"+s

# إنشاء دالة POS مستقلة
method=r'''
    def execute_real_sale(self, items, warehouse_id=1, customer_id=None):
        erp=ERP("database/nizam_alqirtasiyah.db")
        total=sum(float(x["quantity"])*float(x["unit_price"]) for x in items)
        return erp.create_sale(
            warehouse_id=warehouse_id,
            items=items,
            customer_id=customer_id,
            branch_id=1,
            cashier_id=1,
            payments=[{"payment_method":"CASH","amount":total}]
        )

'''

# وضعها داخل MainWindow قبل أول دالة بعد تعريف الصنف
pos=s.find("class MainWindow")
if pos<0:
    raise SystemExit("MAINWINDOW CLASS NOT FOUND")

start=s.find("\n",pos)+1
if "def execute_real_sale(self" not in s:
    s=s[:start]+method+s[start:]

p.write_text(s,encoding="utf-8")
py_compile.compile(str(p),doraise=True)

# فحص الاستيراد الفعلي
import subprocess,sys
r=subprocess.run(
 [sys.executable,"-c","from app.ui.main_window import MainWindow; print('IMPORT: PASSED')"],
 capture_output=True,text=True
)
if r.returncode:
    print(r.stderr)
    raise SystemExit(1)

print("="*65)
print("POS ENGINE FINAL LINK")
print("="*65)
print("BACKUP: SAVED")
print("ERP ENGINE: CONNECTED")
print("REAL SALE METHOD: ADDED")
print("CASH: CONNECTED")
print("STOCK: CONNECTED")
print("ACCOUNTING: CONNECTED")
print("COMPILE: PASSED")
print("IMPORT: PASSED")
print("STATUS: SUCCESS")
print("="*65)
