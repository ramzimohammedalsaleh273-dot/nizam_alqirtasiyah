from pathlib import Path
import shutil

p=Path("app/ui/main_window.py")
backup=Path("backups/main_window_before_real_pos.py")
backup.parent.mkdir(exist_ok=True)
shutil.copy2(p,backup)

s=p.read_text(encoding="utf-8")

old='''        def complete_sale():
            if table.rowCount()==0:
                QMessageBox.warning(dialog,"البيع","أضف منتجًا أولًا.")
                return

            QMessageBox.information(
                dialog,
                "نقطة البيع",
                "تم تجهيز الفاتورة بنجاح.\\n"
                "الربط النهائي مع محرك البيع سيتم في المرحلة التشغيلية التالية."
            )
'''

new='''        def complete_sale():
            if table.rowCount()==0:
                QMessageBox.warning(dialog,"البيع","أضف منتجًا أولًا.")
                return

            try:
                from app.services.erp_engine import ERP

                items=[]
                for r in range(table.rowCount()):
                    sku=table.item(r,1).text().strip()
                    qty=float(table.item(r,3).text())

                    con=sqlite3.connect(db)
                    row=con.execute(
                        "SELECT id,sale_price FROM products WHERE sku=? LIMIT 1",
                        (sku,)
                    ).fetchone()
                    con.close()

                    if not row:
                        raise Exception(f"المنتج غير موجود: {sku}")

                    items.append({
                        "product_id":int(row[0]),
                        "quantity":qty,
                        "unit_price":float(row[1] or 0)
                    })

                engine=ERP(db)
                result=engine.create_sale(
                    warehouse_id=1,
                    items=items,
                    customer_id=None,
                    branch_id=1,
                    cashier_id=1,
                    payments=[{
                        "payment_method":"CASH",
                        "amount":sum(
                            float(table.item(r,4).text())
                            for r in range(table.rowCount())
                        ) * 1.15
                    }],
                    tax_rate=15
                )

                QMessageBox.information(
                    dialog,
                    "تم البيع",
                    f"تم تسجيل البيع فعليًا بنجاح.\\n\\n"
                    f"رقم الفاتورة: {result.get('invoice_number')}\\n"
                    f"الإجمالي: {result.get('total',0):.2f}\\n"
                    f"المدفوع: {result.get('paid',0):.2f)}"
                )

                table.setRowCount(0)
                calculate_total()
                self.refresh_live_dashboard()

            except Exception as e:
                QMessageBox.critical(
                    dialog,
                    "خطأ في تسجيل البيع",
                    str(e)
                )
'''

if old not in s:
    raise SystemExit("لم يتم العثور على دالة البيع التجريبية")

s=s.replace(old,new,1)
p.write_text(s,encoding="utf-8")

print("="*70)
print("REAL POS ENGINE LINK")
print("="*70)
print("BACKUP:",backup)
print("STATUS: SUCCESS")
print("تم ربط POS بمحرك ERP.")
print("="*70)
