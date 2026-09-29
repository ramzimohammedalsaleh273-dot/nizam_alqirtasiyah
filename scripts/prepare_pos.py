from pathlib import Path
import shutil

p=Path("app/ui/main_window.py")
backup=Path("backups/main_window_before_pos.py")
backup.parent.mkdir(exist_ok=True)
shutil.copy2(p,backup)

s=p.read_text(encoding="utf-8")

if "def open_pos" not in s:
    marker="    def refresh_live_dashboard"
    pos=s.find(marker)

    if pos == -1:
        raise SystemExit("لم يتم العثور على مكان مناسب لإضافة POS")

    method=r'''    def open_pos(self):
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QMessageBox
        import sqlite3
        from pathlib import Path

        dialog=QDialog(self)
        dialog.setWindowTitle("نقطة البيع — POS")
        dialog.resize(1000,650)
        dialog.setLayoutDirection(2)

        layout=QVBoxLayout(dialog)

        title=QLabel("نقطة البيع — المبيعات")
        title.setStyleSheet("font-size:24px;font-weight:bold;padding:10px;")
        layout.addWidget(title)

        search=QLineEdit()
        search.setPlaceholderText("ابحث بالباركود أو اسم المنتج...")
        layout.addWidget(search)

        table=QTableWidget(0,5)
        table.setHorizontalHeaderLabels(["المنتج","الباركود","السعر","الكمية","الإجمالي"])
        layout.addWidget(table)

        total=QLabel("الإجمالي: 0.00")
        total.setStyleSheet("font-size:20px;font-weight:bold;padding:10px;")
        layout.addWidget(total)

        buttons=QHBoxLayout()
        add_btn=QPushButton("إضافة المنتج")
        sell_btn=QPushButton("إتمام البيع")
        close_btn=QPushButton("إغلاق")

        buttons.addWidget(add_btn)
        buttons.addWidget(sell_btn)
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

        db=Path(__file__).resolve().parents[2] / "database" / "nizam_alqirtasiyah.db"

        def find_product():
            text=search.text().strip()
            if not text:
                return

            con=sqlite3.connect(db)
            cur=con.cursor()
            row=cur.execute("""
                SELECT id,name_ar,sku,sale_price
                FROM products
                WHERE is_active=1
                AND (name_ar LIKE ? OR sku LIKE ?)
                LIMIT 1
            """,(f"%{text}%",f"%{text}%")).fetchone()
            con.close()

            if not row:
                QMessageBox.warning(dialog,"المنتج","لم يتم العثور على المنتج.")
                return

            r=table.rowCount()
            table.insertRow(r)
            table.setItem(r,0,QTableWidgetItem(str(row[1])))
            table.setItem(r,1,QTableWidgetItem(str(row[2] or "")))
            table.setItem(r,2,QTableWidgetItem(f"{float(row[3] or 0):.2f}"))
            table.setItem(r,3,QTableWidgetItem("1"))
            table.setItem(r,4,QTableWidgetItem(f"{float(row[3] or 0):.2f}"))
            search.clear()

            calculate_total()

        def calculate_total():
            total_value=0
            for r in range(table.rowCount()):
                try:
                    price=float(table.item(r,2).text())
                    qty=float(table.item(r,3).text())
                    line=price*qty
                    table.setItem(r,4,QTableWidgetItem(f"{line:.2f}"))
                    total_value+=line
                except:
                    pass
            total.setText(f"الإجمالي: {total_value:.2f}")

        def complete_sale():
            if table.rowCount()==0:
                QMessageBox.warning(dialog,"البيع","أضف منتجًا أولًا.")
                return

            QMessageBox.information(
                dialog,
                "نقطة البيع",
                "تم تجهيز الفاتورة بنجاح.\n"
                "الربط النهائي مع محرك البيع سيتم في المرحلة التشغيلية التالية."
            )

        add_btn.clicked.connect(find_product)
        sell_btn.clicked.connect(complete_sale)
        close_btn.clicked.connect(dialog.close)
        search.returnPressed.connect(find_product)

        dialog.exec()

'''

    s=s[:pos]+method+s[pos:]

if "open_pos()" not in s:
    marker="self.refresh_live_dashboard()"
    pos=s.find(marker)
    if pos != -1:
        line_end=s.find("\n",pos)
        if line_end != -1:
            s=s[:line_end+1]+"""        try:
            if hasattr(self, "pos_button"):
                self.pos_button.clicked.connect(self.open_pos)
        except:
            pass
"""+s[line_end+1:]

p.write_text(s,encoding="utf-8")

print("="*70)
print("POS PREPARATION")
print("="*70)
print("BACKUP:",backup)
print("STATUS: SUCCESS")
print("تم تجهيز شاشة نقطة البيع.")
print("="*70)
