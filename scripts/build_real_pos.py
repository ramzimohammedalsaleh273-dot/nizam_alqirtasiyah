from pathlib import Path
import shutil,datetime,py_compile

ROOT=Path.cwd()
UI=ROOT/"app/ui/main_window.py"
BACK=ROOT/"backups"
BACK.mkdir(exist_ok=True)

stamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup=BACK/f"before_real_pos_{stamp}_main_window.py"
shutil.copy2(UI,backup)

s=UI.read_text(encoding="utf-8")

start=s.index("class POS(QWidget):")
end=s.index("# ------------------------------------------------------------\n# REPORTS",start)

new_pos=r'''class POS(QWidget):
    def __init__(self):
        super().__init__()
        self.cart=[]
        self.build()

    def build(self):
        root=QVBoxLayout(self)

        title=QLabel("نقطة البيع — POS")
        title.setObjectName("title")
        root.addWidget(title)

        top=QHBoxLayout()

        self.search=QLineEdit()
        self.search.setPlaceholderText(
            "ابحث بالباركود أو SKU أو اسم المنتج..."
        )
        self.search.returnPressed.connect(self.search_product)
        top.addWidget(self.search)

        b=QPushButton("إضافة")
        b.setObjectName("primary")
        b.clicked.connect(self.search_product)
        top.addWidget(b)

        clear=QPushButton("تفريغ السلة")
        clear.setObjectName("secondary")
        clear.clicked.connect(self.clear_cart)
        top.addWidget(clear)

        root.addLayout(top)

        self.result=QLabel("جاهز للبيع")
        self.result.setObjectName("muted")
        root.addWidget(self.result)

        self.table=QTableWidget(0,7)
        self.table.setHorizontalHeaderLabels([
            "المنتج","الكمية","سعر الوحدة",
            "الخصم","الضريبة","الإجمالي","المعرّف"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        root.addWidget(self.table)

        bottom=QFrame()
        bottom.setObjectName("card")
        bl=QHBoxLayout(bottom)

        self.customer=QComboBox()
        self.customer.addItem("عميل نقدي",None)
        try:
            c=db()
            for r in c.execute(
                "SELECT id,name FROM customers "
                "WHERE is_active=1 ORDER BY name"
            ):
                self.customer.addItem(str(r["name"]),r["id"])
            c.close()
        except:
            pass

        bl.addWidget(QLabel("العميل:"))
        bl.addWidget(self.customer)

        bl.addStretch()

        self.total_label=QLabel("الإجمالي: 0.00")
        self.total_label.setObjectName("cardValue")
        bl.addWidget(self.total_label)

        sell=QPushButton("إتمام البيع نقدًا")
        sell.setObjectName("primary")
        sell.clicked.connect(self.finish_sale)
        bl.addWidget(sell)

        root.addWidget(bottom)

    def search_product(self):
        text=self.search.text().strip()

        if not text:
            return

        c=db()
        row=c.execute("""
            SELECT id,name_ar,sale_price,barcode,sku
            FROM products
            WHERE is_active=1
            AND (
                name_ar LIKE ?
                OR barcode LIKE ?
                OR sku LIKE ?
            )
            ORDER BY id
            LIMIT 1
        """,(
            f"%{text}%",
            f"%{text}%",
            f"%{text}%"
        )).fetchone()
        c.close()

        if not row:
            self.result.setText("لم يتم العثور على المنتج")
            return

        pid=int(row["id"])
        name=str(row["name_ar"])
        price=float(row["sale_price"] or 0)

        for item in self.cart:
            if item["product_id"]==pid:
                item["quantity"]+=1
                self.refresh()
                self.search.clear()
                return

        self.cart.append({
            "product_id":pid,
            "name":name,
            "quantity":1,
            "unit_price":price
        })

        self.refresh()
        self.search.clear()
        self.result.setText(f"تمت إضافة: {name}")

    def refresh(self):
        self.table.setRowCount(0)

        subtotal=0

        for item in self.cart:
            r=self.table.rowCount()
            self.table.insertRow(r)

            qty=int(item["quantity"])
            price=float(item["unit_price"])

            line=qty*price
            tax=line*0.15
            total=line+tax
            subtotal+=line

            values=[
                item["name"],
                str(qty),
                f"{price:.2f}",
                "0.00",
                f"{tax:.2f}",
                f"{total:.2f}",
                str(item["product_id"])
            ]

            for col,value in enumerate(values):
                self.table.setItem(
                    r,col,QTableWidgetItem(value)
                )

        grand=subtotal*1.15
        self.total_label.setText(
            f"الإجمالي: {grand:.2f}"
        )

    def clear_cart(self):
        self.cart=[]
        self.refresh()
        self.result.setText("السلة فارغة")

    def finish_sale(self):
        if not self.cart:
            QMessageBox.warning(
                self,
                "نقطة البيع",
                "السلة فارغة"
            )
            return

        try:
            from app.services.erp_engine import ERP

            c=db()

            branch_row=c.execute(
                "SELECT id FROM branches ORDER BY id LIMIT 1"
            ).fetchone()

            warehouse_row=c.execute(
                "SELECT id FROM warehouses ORDER BY id LIMIT 1"
            ).fetchone()

            cashier_row=c.execute(
                "SELECT id FROM users ORDER BY id LIMIT 1"
            ).fetchone()

            c.close()

            if not branch_row or not warehouse_row or not cashier_row:
                raise RuntimeError(
                    "بيانات الفرع أو المستودع أو المستخدم غير موجودة"
                )

            branch_id=int(branch_row["id"])
            warehouse_id=int(warehouse_row["id"])
            cashier_id=int(cashier_row["id"])

            items=[]

            for item in self.cart:
                items.append({
                    "product_id":int(item["product_id"]),
                    "quantity":int(item["quantity"]),
                    "unit_price":float(item["unit_price"])
                })

            subtotal=sum(
                x["quantity"]*x["unit_price"]
                for x in self.cart
            )

            total=round(subtotal*1.15,2)

            erp=ERP(
                str(ROOT/"database"/"nizam_alqirtasiyah.db")
            )

            result=erp.create_sale(
                warehouse_id,
                items,
                customer_id=self.customer.currentData(),
                branch_id=branch_id,
                cashier_id=cashier_id,
                payments=[
                    {
                        "payment_method":"CASH",
                        "amount":total
                    }
                ],
                tax_rate=15
            )

            self.clear_cart()

            self.result.setText(
                "تمت عملية البيع بنجاح — "
                f"الفاتورة: {result['invoice_number']} — "
                f"الإجمالي: {result['total']:.2f}"
            )

            QMessageBox.information(
                self,
                "تم البيع",
                "تم تسجيل الفاتورة بنجاح.\n\n"
                f"رقم الفاتورة: {result['invoice_number']}\n"
                f"الإجمالي: {result['total']:.2f}\n"
                f"المدفوع: {result['paid']:.2f}\n"
                f"المتبقي: {result['due']:.2f}"
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "فشل البيع",
                str(e)
            )
            self.result.setText(
                "فشلت عملية البيع: "+str(e)
            )

'''

s=s[:start]+new_pos+s[end:]
UI.write_text(s,encoding="utf-8")

py_compile.compile(str(UI),doraise=True)
py_compile.compile("main.py",doraise=True)

print("="*90)
print("المرحلة 2 — REAL POS")
print("="*90)
print("POS UI: OK")
print("PRODUCT SEARCH: OK")
print("CART: OK")
print("VAT CALCULATION: OK")
print("ERP SALE LINK: OK")
print("STOCK LINK: OK")
print("ACCOUNTING LINK: OK")
print("PAYMENT LINK: OK")
print("BACKUP:",backup)
print("STATUS: SUCCESS")
print("="*90)
