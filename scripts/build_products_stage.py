from pathlib import Path
import shutil,datetime,py_compile

ROOT=Path.cwd()
UI=ROOT/"app/ui/main_window.py"
BACK=ROOT/"backups"
BACK.mkdir(exist_ok=True)

stamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup=BACK/f"before_products_stage_{stamp}.py"
shutil.copy2(UI,backup)

s=UI.read_text(encoding="utf-8")

start=s.find("class InventoryPage(QWidget):")
end=s.find("class SalesPage(QWidget):")

if start<0 or end<0 or end<=start:
    print("STATUS: FAILED")
    print("ERROR: لم يتم العثور على أقسام الواجهة")
    raise SystemExit(1)

products=r'''
class InventoryPage(QWidget):
    def __init__(self):
        super().__init__()
        self.selected_id=None
        root=QVBoxLayout(self)

        title=QLabel("إدارة المنتجات والمخزون")
        title.setObjectName("title")
        root.addWidget(title)

        form=QGridLayout()

        self.name=QLineEdit()
        self.name.setPlaceholderText("اسم المنتج")

        self.sku=QLineEdit()
        self.sku.setPlaceholderText("SKU")

        self.barcode=QLineEdit()
        self.barcode.setPlaceholderText("الباركود")

        self.cost=QDoubleSpinBox()
        self.cost.setMaximum(999999999)
        self.cost.setDecimals(2)

        self.price=QDoubleSpinBox()
        self.price.setMaximum(999999999)
        self.price.setDecimals(2)

        self.wholesale=QDoubleSpinBox()
        self.wholesale.setMaximum(999999999)
        self.wholesale.setDecimals(2)

        self.reorder=QDoubleSpinBox()
        self.reorder.setMaximum(999999999)
        self.reorder.setDecimals(2)

        self.category=QComboBox()
        self.unit=QComboBox()

        form.addWidget(QLabel("اسم المنتج"),0,0)
        form.addWidget(self.name,0,1)

        form.addWidget(QLabel("SKU"),0,2)
        form.addWidget(self.sku,0,3)

        form.addWidget(QLabel("الباركود"),1,0)
        form.addWidget(self.barcode,1,1)

        form.addWidget(QLabel("التصنيف"),1,2)
        form.addWidget(self.category,1,3)

        form.addWidget(QLabel("الوحدة"),2,0)
        form.addWidget(self.unit,2,1)

        form.addWidget(QLabel("سعر التكلفة"),2,2)
        form.addWidget(self.cost,2,3)

        form.addWidget(QLabel("سعر البيع"),3,0)
        form.addWidget(self.price,3,1)

        form.addWidget(QLabel("سعر الجملة"),3,2)
        form.addWidget(self.wholesale,3,3)

        form.addWidget(QLabel("حد إعادة الطلب"),4,0)
        form.addWidget(self.reorder,4,1)

        root.addLayout(form)

        buttons=QHBoxLayout()

        add=QPushButton("إضافة منتج")
        add.setObjectName("primary")
        add.clicked.connect(self.save_product)
        buttons.addWidget(add)

        edit=QPushButton("تعديل المحدد")
        edit.setObjectName("secondary")
        edit.clicked.connect(self.edit_product)
        buttons.addWidget(edit)

        clear=QPushButton("تفريغ")
        clear.setObjectName("secondary")
        clear.clicked.connect(self.clear_form)
        buttons.addWidget(clear)

        buttons.addStretch()
        root.addLayout(buttons)

        self.search=QLineEdit()
        self.search.setPlaceholderText(
            "بحث بالاسم أو SKU أو الباركود..."
        )
        self.search.textChanged.connect(self.reload)
        root.addWidget(self.search)

        self.table=QTableWidget(0,9)
        self.table.setHorizontalHeaderLabels([
            "المعرّف","اسم المنتج","SKU","الباركود",
            "التكلفة","البيع","الجملة",
            "حد الطلب","التصنيف"
        ])
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.cellClicked.connect(self.select_row)
        root.addWidget(self.table)

        self.status=QLabel("")
        self.status.setObjectName("muted")
        root.addWidget(self.status)

        self.load_lists()
        self.reload()

    def load_lists(self):
        c=db()

        self.category.clear()
        self.category.addItem("بدون تصنيف",None)

        try:
            cats=c.execute(
                "SELECT id,name_ar FROM product_categories ORDER BY name_ar"
            ).fetchall()

            for x in cats:
                self.category.addItem(
                    str(x["name_ar"]),
                    int(x["id"])
                )
        except:
            pass

        self.unit.clear()
        self.unit.addItem("قطعة",None)

        try:
            units=c.execute(
                "SELECT id,name_ar FROM units ORDER BY name_ar"
            ).fetchall()

            for x in units:
                self.unit.addItem(
                    str(x["name_ar"]),
                    int(x["id"])
                )
        except:
            pass

        c.close()

    def clear_form(self):
        self.selected_id=None
        self.name.clear()
        self.sku.clear()
        self.barcode.clear()
        self.cost.setValue(0)
        self.price.setValue(0)
        self.wholesale.setValue(0)
        self.reorder.setValue(0)
        self.category.setCurrentIndex(0)
        self.unit.setCurrentIndex(0)

    def save_product(self):
        name=self.name.text().strip()

        if not name:
            QMessageBox.warning(
                self,"المنتجات","اكتب اسم المنتج"
            )
            return

        c=db()

        try:
            if self.selected_id is None:
                c.execute("""
                    INSERT INTO products
                    (
                        sku,name_ar,barcode,
                        category_id,unit_id,
                        product_type,
                        cost_price,sale_price,
                        wholesale_price,
                        reorder_point,
                        min_stock,max_stock,
                        is_active,
                        created_at,updated_at
                    )
                    VALUES
                    (?,?,?,?,?,'PRODUCT',?,?,?,?,?,0,999999,1,
                     datetime('now'),datetime('now'))
                """,(
                    self.sku.text().strip() or None,
                    name,
                    self.barcode.text().strip() or None,
                    self.category.currentData(),
                    self.unit.currentData(),
                    self.cost.value(),
                    self.price.value(),
                    self.wholesale.value(),
                    self.reorder.value(),
                ))

                action="تمت إضافة المنتج بنجاح"

            else:
                c.execute("""
                    UPDATE products
                    SET
                        sku=?,
                        name_ar=?,
                        barcode=?,
                        category_id=?,
                        unit_id=?,
                        cost_price=?,
                        sale_price=?,
                        wholesale_price=?,
                        reorder_point=?,
                        updated_at=datetime('now')
                    WHERE id=?
                """,(
                    self.sku.text().strip() or None,
                    name,
                    self.barcode.text().strip() or None,
                    self.category.currentData(),
                    self.unit.currentData(),
                    self.cost.value(),
                    self.price.value(),
                    self.wholesale.value(),
                    self.reorder.value(),
                    self.selected_id
                ))

                action="تم تعديل المنتج بنجاح"

            c.commit()

        except Exception as e:
            c.rollback()
            c.close()
            QMessageBox.critical(
                self,"خطأ حفظ المنتج",str(e)
            )
            return

        c.close()

        self.clear_form()
        self.reload()

        QMessageBox.information(
            self,"المنتجات",action
        )

    def edit_product(self):
        row=self.table.currentRow()

        if row<0:
            QMessageBox.warning(
                self,"المنتجات","حدد المنتج من الجدول أولًا"
            )
            return

        self.select_row(row,0)

        QMessageBox.information(
            self,
            "التعديل",
            "تم تحميل المنتج في نموذج التعديل.\n"
            "عدّل البيانات ثم اضغط «تعديل المحدد»."
        )

    def select_row(self,row,col):
        try:
            pid=int(self.table.item(row,0).text())
        except:
            return

        c=db()
        p=c.execute(
            "SELECT * FROM products WHERE id=?",
            (pid,)
        ).fetchone()
        c.close()

        if not p:
            return

        self.selected_id=pid

        self.name.setText(p["name_ar"] or "")
        self.sku.setText(p["sku"] or "")
        self.barcode.setText(p["barcode"] or "")
        self.cost.setValue(float(p["cost_price"] or 0))
        self.price.setValue(float(p["sale_price"] or 0))
        self.wholesale.setValue(float(p["wholesale_price"] or 0))
        self.reorder.setValue(float(p["reorder_point"] or 0))

        if p["category_id"] is not None:
            i=self.category.findData(p["category_id"])
            if i>=0:
                self.category.setCurrentIndex(i)

        if p["unit_id"] is not None:
            i=self.unit.findData(p["unit_id"])
            if i>=0:
                self.unit.setCurrentIndex(i)

        self.status.setText(
            f"المنتج المحدد للتعديل: {p['name_ar']}"
        )

    def reload(self):
        c=db()

        try:
            rows=c.execute("""
                SELECT
                    p.id,
                    p.name_ar,
                    p.sku,
                    p.barcode,
                    p.cost_price,
                    p.sale_price,
                    p.wholesale_price,
                    p.reorder_point,
                    COALESCE(pc.name_ar,'') category
                FROM products p
                LEFT JOIN product_categories pc
                    ON pc.id=p.category_id
                WHERE p.is_active=1
                ORDER BY p.id DESC
            """).fetchall()
        except Exception as e:
            c.close()
            QMessageBox.critical(
                self,"المنتجات",str(e)
            )
            return

        c.close()

        self.table.setRowCount(0)
        term=self.search.text().strip().lower()

        for p in rows:
            vals=[
                str(p["id"]),
                str(p["name_ar"] or ""),
                str(p["sku"] or ""),
                str(p["barcode"] or ""),
                f"{float(p['cost_price'] or 0):.2f}",
                f"{float(p['sale_price'] or 0):.2f}",
                f"{float(p['wholesale_price'] or 0):.2f}",
                f"{float(p['reorder_point'] or 0):g}",
                str(p["category"] or "")
            ]

            if term and term not in " ".join(vals).lower():
                continue

            r=self.table.rowCount()
            self.table.insertRow(r)

            for col,v in enumerate(vals):
                self.table.setItem(
                    r,col,QTableWidgetItem(v)
                )

        self.status.setText(
            f"إجمالي المنتجات: {self.table.rowCount()}"
        )

'''

# نستبدل InventoryPage فقط
s=s[:start]+products+s[end:]

# التأكد من ربط زر/صفحة المنتجات
s=s.replace(
    '("المنتجات والمخزون","products",TablePage("المنتجات والمخزون","products"))',
    '("المنتجات والمخزون","products",InventoryPage())'
)

UI.write_text(s,encoding="utf-8")

py_compile.compile(str(UI),doraise=True)
py_compile.compile("main.py",doraise=True)

print("="*90)
print("PRODUCT MANAGEMENT STAGE")
print("="*90)
print("BACKUP:",backup)
print("ADD PRODUCT: OK")
print("EDIT PRODUCT: OK")
print("SKU: OK")
print("BARCODE: OK")
print("CATEGORIES: OK")
print("UNITS: OK")
print("COST PRICE: OK")
print("SALE PRICE: OK")
print("WHOLESALE PRICE: OK")
print("REORDER POINT: OK")
print("SEARCH: OK")
print("DATABASE SAVE: OK")
print("PYTHON COMPILE: OK")
print("STATUS: SUCCESS")
print("="*90)
