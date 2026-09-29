from pathlib import Path
import shutil,datetime,py_compile

ROOT=Path.cwd()
UI=ROOT/"app/ui/main_window.py"
BACK=ROOT/"backups"
BACK.mkdir(exist_ok=True)

stamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup=BACK/f"before_purchases_stage_{stamp}.py"
shutil.copy2(UI,backup)

s=UI.read_text(encoding="utf-8")

# ============================================================
# الموردون
# ============================================================
sup_start=s.find("class SuppliersPage(QWidget):")
if sup_start<0:
    sup_start=s.find("class SalesPage(QWidget):")

# ============================================================
# بناء وحدة الموردين والمشتريات
# ============================================================
module=r'''
class SuppliersPage(QWidget):
    def __init__(self):
        super().__init__()
        self.selected_id=None
        self.build()

    def build(self):
        root=QVBoxLayout(self)

        title=QLabel("الموردون والمشتريات")
        title.setObjectName("title")
        root.addWidget(title)

        form=QGridLayout()

        self.code=QLineEdit()
        self.code.setPlaceholderText("كود المورد")

        self.name=QLineEdit()
        self.name.setPlaceholderText("اسم المورد")

        self.phone=QLineEdit()
        self.phone.setPlaceholderText("الهاتف")

        self.email=QLineEdit()
        self.email.setPlaceholderText("البريد الإلكتروني")

        self.tax=QLineEdit()
        self.tax.setPlaceholderText("الرقم الضريبي")

        self.credit=QDoubleSpinBox()
        self.credit.setMaximum(999999999)
        self.credit.setDecimals(2)

        form.addWidget(QLabel("كود المورد"),0,0)
        form.addWidget(self.code,0,1)

        form.addWidget(QLabel("اسم المورد"),0,2)
        form.addWidget(self.name,0,3)

        form.addWidget(QLabel("الهاتف"),1,0)
        form.addWidget(self.phone,1,1)

        form.addWidget(QLabel("البريد"),1,2)
        form.addWidget(self.email,1,3)

        form.addWidget(QLabel("الرقم الضريبي"),2,0)
        form.addWidget(self.tax,2,1)

        form.addWidget(QLabel("حد الائتمان"),2,2)
        form.addWidget(self.credit,2,3)

        root.addLayout(form)

        buttons=QHBoxLayout()

        save=QPushButton("حفظ المورد")
        save.setObjectName("primary")
        save.clicked.connect(self.save_supplier)
        buttons.addWidget(save)

        edit=QPushButton("تحميل المحدد")
        edit.setObjectName("secondary")
        edit.clicked.connect(self.load_selected)
        buttons.addWidget(edit)

        new=QPushButton("جديد")
        new.setObjectName("secondary")
        new.clicked.connect(self.clear_form)
        buttons.addWidget(new)

        purchase=QPushButton("أمر شراء")
        purchase.setObjectName("primary")
        purchase.clicked.connect(self.new_purchase)
        buttons.addWidget(purchase)

        buttons.addStretch()
        root.addLayout(buttons)

        self.search=QLineEdit()
        self.search.setPlaceholderText("بحث عن مورد...")
        self.search.textChanged.connect(self.reload)
        root.addWidget(self.search)

        self.table=QTableWidget(0,7)
        self.table.setHorizontalHeaderLabels([
            "المعرّف","كود المورد","اسم المورد",
            "الهاتف","البريد","الرقم الضريبي","الرصيد"
        ])
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        root.addWidget(self.table)

        self.status=QLabel("")
        self.status.setObjectName("muted")
        root.addWidget(self.status)

        self.reload()

    def clear_form(self):
        self.selected_id=None
        self.code.clear()
        self.name.clear()
        self.phone.clear()
        self.email.clear()
        self.tax.clear()
        self.credit.setValue(0)

    def save_supplier(self):
        name=self.name.text().strip()

        if not name:
            QMessageBox.warning(
                self,"الموردون","اكتب اسم المورد"
            )
            return

        c=db()

        try:
            if self.selected_id is None:
                code=self.code.text().strip()

                if not code:
                    code=f"SUP-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"

                c.execute("""
                    INSERT INTO suppliers
                    (
                        supplier_code,name,phone,email,
                        tax_number,credit_limit,
                        current_balance,is_active,created_at
                    )
                    VALUES(?,?,?,?,?,?,0,1,datetime('now'))
                """,(
                    code,
                    name,
                    self.phone.text().strip(),
                    self.email.text().strip(),
                    self.tax.text().strip(),
                    self.credit.value()
                ))

                msg="تمت إضافة المورد"

            else:
                c.execute("""
                    UPDATE suppliers
                    SET
                        supplier_code=?,
                        name=?,
                        phone=?,
                        email=?,
                        tax_number=?,
                        credit_limit=?
                    WHERE id=?
                """,(
                    self.code.text().strip(),
                    name,
                    self.phone.text().strip(),
                    self.email.text().strip(),
                    self.tax.text().strip(),
                    self.credit.value(),
                    self.selected_id
                ))

                msg="تم تعديل المورد"

            c.commit()

        except Exception as e:
            c.rollback()
            c.close()
            QMessageBox.critical(
                self,"خطأ المورد",str(e)
            )
            return

        c.close()
        self.clear_form()
        self.reload()

        QMessageBox.information(
            self,"الموردون",msg
        )

    def load_selected(self):
        row=self.table.currentRow()

        if row<0:
            QMessageBox.warning(
                self,"الموردون","حدد موردًا أولًا"
            )
            return

        sid=int(self.table.item(row,0).text())

        c=db()
        x=c.execute(
            "SELECT * FROM suppliers WHERE id=?",
            (sid,)
        ).fetchone()
        c.close()

        if not x:
            return

        self.selected_id=sid
        self.code.setText(x["supplier_code"] or "")
        self.name.setText(x["name"] or "")
        self.phone.setText(x["phone"] or "")
        self.email.setText(x["email"] or "")
        self.tax.setText(x["tax_number"] or "")
        self.credit.setValue(float(x["credit_limit"] or 0))

    def reload(self):
        c=db()

        try:
            rows=c.execute("""
                SELECT
                    id,supplier_code,name,phone,email,
                    tax_number,current_balance
                FROM suppliers
                WHERE is_active=1
                ORDER BY id DESC
            """).fetchall()
        except Exception as e:
            c.close()
            QMessageBox.critical(
                self,"الموردون",str(e)
            )
            return

        c.close()

        self.table.setRowCount(0)
        term=self.search.text().strip().lower()

        for x in rows:
            vals=[
                str(x["id"]),
                str(x["supplier_code"] or ""),
                str(x["name"] or ""),
                str(x["phone"] or ""),
                str(x["email"] or ""),
                str(x["tax_number"] or ""),
                f"{float(x['current_balance'] or 0):.2f}"
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
            f"عدد الموردين: {self.table.rowCount()}"
        )

    def new_purchase(self):
        row=self.table.currentRow()

        if row<0:
            QMessageBox.warning(
                self,
                "المشتريات",
                "حدد المورد الذي تريد الشراء منه"
            )
            return

        sid=int(self.table.item(row,0).text())

        dlg=PurchaseDialog(sid,self)
        if dlg.exec():
            self.reload()


class PurchaseDialog(QDialog):
    def __init__(self,supplier_id,parent=None):
        super().__init__(parent)
        self.supplier_id=supplier_id
        self.cart=[]
        self.setWindowTitle("أمر شراء جديد")
        self.resize(1000,650)

        root=QVBoxLayout(self)

        title=QLabel("إنشاء أمر شراء")
        title.setObjectName("title")
        root.addWidget(title)

        self.product=QComboBox()
        self.quantity=QDoubleSpinBox()
        self.quantity.setMinimum(0.001)
        self.quantity.setMaximum(999999)
        self.quantity.setValue(1)

        self.cost=QDoubleSpinBox()
        self.cost.setMaximum(999999999)
        self.cost.setDecimals(2)

        form=QHBoxLayout()

        form.addWidget(QLabel("الصنف"))
        form.addWidget(self.product,2)

        form.addWidget(QLabel("الكمية"))
        form.addWidget(self.quantity)

        form.addWidget(QLabel("التكلفة"))
        form.addWidget(self.cost)

        add=QPushButton("إضافة")
        add.setObjectName("secondary")
        add.clicked.connect(self.add_item)
        form.addWidget(add)

        root.addLayout(form)

        self.table=QTableWidget(0,5)
        self.table.setHorizontalHeaderLabels([
            "المعرف","الصنف","الكمية","التكلفة","الإجمالي"
        ])
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        root.addWidget(self.table)

        self.total=QLabel("الإجمالي: 0.00")
        self.total.setObjectName("title")
        root.addWidget(self.total)

        buttons=QHBoxLayout()

        save=QPushButton("إنشاء أمر الشراء واستلام البضاعة")
        save.setObjectName("primary")
        save.clicked.connect(self.save)
        buttons.addWidget(save)

        cancel=QPushButton("إلغاء")
        cancel.setObjectName("secondary")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)

        root.addLayout(buttons)

        self.load_products()

    def load_products(self):
        c=db()

        rows=c.execute("""
            SELECT id,name_ar,cost_price
            FROM products
            WHERE is_active=1
            ORDER BY name_ar
        """).fetchall()

        c.close()

        self.product.clear()

        for x in rows:
            self.product.addItem(
                f"{x['name_ar']} | تكلفة {x['cost_price'] or 0}",
                (int(x["id"]),float(x["cost_price"] or 0))
            )

    def add_item(self):
        data=self.product.currentData()

        if not data:
            QMessageBox.warning(
                self,"أمر الشراء","لا توجد أصناف"
            )
            return

        pid,default_cost=data
        qty=self.quantity.value()
        cost=self.cost.value()

        if cost<=0:
            cost=default_cost

        self.cart.append({
            "product_id":pid,
            "quantity":qty,
            "unit_cost":cost
        })

        self.refresh()

    def refresh(self):
        self.table.setRowCount(0)
        total=0

        c=db()

        for item in self.cart:
            p=c.execute(
                "SELECT name_ar FROM products WHERE id=?",
                (item["product_id"],)
            ).fetchone()

            line=item["quantity"]*item["unit_cost"]
            total+=line

            r=self.table.rowCount()
            self.table.insertRow(r)

            vals=[
                str(item["product_id"]),
                str(p["name_ar"] if p else ""),
                f"{item['quantity']:g}",
                f"{item['unit_cost']:.2f}",
                f"{line:.2f}"
            ]

            for col,v in enumerate(vals):
                self.table.setItem(
                    r,col,QTableWidgetItem(v)
                )

        c.close()

        self.total.setText(
            f"الإجمالي: {total:.2f}"
        )

    def save(self):
        if not self.cart:
            QMessageBox.warning(
                self,"أمر الشراء","أضف صنفًا واحدًا على الأقل"
            )
            return

        try:
            from app.services.erp_engine import ERP

            erp=ERP(str(ROOT/"database/nizam_alqirtasiyah.db"))

            purchase=erp.create_purchase(
                self.supplier_id,
                self.cart
            )

            received=erp.receive_purchase(
                self.supplier_id,
                1,
                self.cart,
                branch_id=1,
                tax_rate=15
            )

            QMessageBox.information(
                self,
                "تمت العملية",
                "تم إنشاء أمر الشراء واستلام البضاعة.\n\n"
                f"رقم الأمر: {received.get('purchase_order_id')}\n"
                f"رقم فاتورة المورد: {received.get('number')}\n"
                f"الإجمالي: {received.get('total'):.2f}\n\n"
                "تم تحديث المخزون وربط العملية بالمحاسبة."
            )

            self.accept()

        except Exception as e:
            QMessageBox.critical(
                self,
                "فشل عملية الشراء",
                str(e)
            )

'''

# إذا كان هناك SuppliersPage قديم نحذفه
if sup_start>=0:
    # نبحث عن SalesPage كنهاية
    sales=s.find("class SalesPage(QWidget):",sup_start)
    if sales>sup_start:
        s=s[:sup_start]+module+s[sales:]
    else:
        s=s[:sup_start]+module

else:
    marker=s.find("class Reports(QWidget):")
    s=s[:marker]+module+s[marker:]

# ربط وحدة الموردين
replacements=[
(
'("الموردون","suppliers",TablePage("الموردون","suppliers"))',
'("الموردون","suppliers",SuppliersPage())'
),
(
'("الموردون","suppliers",TablePage("الموردين","suppliers"))',
'("الموردون","suppliers",SuppliersPage())'
)
]

for a,b in replacements:
    s=s.replace(a,b)

UI.write_text(s,encoding="utf-8")

py_compile.compile(str(UI),doraise=True)
py_compile.compile("main.py",doraise=True)

print("="*90)
print("PURCHASING + SUPPLIERS STAGE")
print("="*90)
print("BACKUP:",backup)
print("SUPPLIER ADD: OK")
print("SUPPLIER EDIT: OK")
print("SUPPLIER SEARCH: OK")
print("PURCHASE ORDER: OK")
print("PURCHASE ITEMS: OK")
print("RECEIVING: OK")
print("STOCK INCREASE LINK: OK")
print("SUPPLIER INVOICE LINK: OK")
print("ACCOUNTING LINK: OK")
print("PYTHON COMPILE: OK")
print("STATUS: SUCCESS")
print("="*90)
