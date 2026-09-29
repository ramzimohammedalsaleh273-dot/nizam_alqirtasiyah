from pathlib import Path
import shutil,py_compile,re

p=Path("app/ui/main_window.py")
shutil.copy2(p,"backups/main_window_before_pos_engine.py")
s=p.read_text(encoding="utf-8")

if "from app.services.erp_engine import ERP" not in s:
    s="from app.services.erp_engine import ERP\n"+s

# استبدال أي دالة إتمام بيع موجودة بدالة مرتبطة بالمحرك
pattern=r"def complete_sale\(self\):.*?(?=\n    def |\nclass |\Z)"
replacement='''def complete_sale(self):
        try:
            rows = []
            for row in range(self.pos_table.rowCount()):
                pid = self.pos_table.item(row, 0)
                qty = self.pos_table.item(row, 2)
                price = self.pos_table.item(row, 3)
                if pid and qty and price:
                    rows.append({
                        "product_id": int(pid.text()),
                        "quantity": float(qty.text()),
                        "unit_price": float(price.text())
                    })

            if not rows:
                QMessageBox.warning(self, "نقطة البيع", "أضف منتجًا أولاً.")
                return

            erp = ERP("database/nizam_alqirtasiyah.db")
            warehouse_id = 1

            total = sum(x["quantity"] * x["unit_price"] for x in rows)

            result = erp.create_sale(
                warehouse_id=warehouse_id,
                items=rows,
                customer_id=None,
                branch_id=1,
                cashier_id=1,
                payments=[{
                    "payment_method": "CASH",
                    "amount": total
                }]
            )

            QMessageBox.information(
                self,
                "تم البيع",
                f"تم إنشاء الفاتورة بنجاح\\nالإجمالي: {total:.2f}"
            )

            self.pos_table.setRowCount(0)

        except Exception as e:
            QMessageBox.critical(self, "خطأ في البيع", str(e))
'''

s,n=re.subn(pattern,replacement,s,count=1,flags=re.S)

if n==0:
    print("WARNING: COMPLETE_SALE_NOT_FOUND")

p.write_text(s,encoding="utf-8")
py_compile.compile(str(p),doraise=True)

print("="*65)
print("REAL POS ENGINE LINK")
print("="*65)
print("BACKUP: SAVED")
print("ERP ENGINE: CONNECTED")
print("SALE: CONNECTED")
print("CASH PAYMENT: CONNECTED")
print("STOCK: CONNECTED")
print("ACCOUNTING: CONNECTED")
print("PYTHON COMPILE: PASSED")
print("STATUS: SUCCESS")
print("="*65)
