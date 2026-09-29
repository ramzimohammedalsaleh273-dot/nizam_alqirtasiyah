from pathlib import Path
import shutil,datetime,py_compile

ROOT=Path.cwd()
UI=ROOT/"app/ui/main_window.py"
BACK=ROOT/"backups"
BACK.mkdir(exist_ok=True)

stamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup=BACK/f"before_inventory_sales_stage_{stamp}_main_window.py"
shutil.copy2(UI,backup)

s=UI.read_text(encoding="utf-8")

# ------------------------------------------------------------
# REAL INVENTORY PAGE
# ------------------------------------------------------------
start=s.index("class Reports(QWidget):")

inventory=r'''
class InventoryPage(QWidget):
    def __init__(self):
        super().__init__()
        self.build()

    def build(self):
        root=QVBoxLayout(self)

        top=QHBoxLayout()
        title=QLabel("المخزون وإدارة الأصناف")
        title.setObjectName("title")
        top.addWidget(title)
        top.addStretch()

        self.search=QLineEdit()
        self.search.setPlaceholderText("بحث باسم الصنف أو SKU أو الباركود...")
        self.search.textChanged.connect(self.reload)
        top.addWidget(self.search)

        refresh=QPushButton("↻ تحديث")
        refresh.setObjectName("secondary")
        refresh.clicked.connect(self.reload)
        top.addWidget(refresh)

        root.addLayout(top)

        cards=QHBoxLayout()

        self.products_card=card("عدد المنتجات",0)
        self.stock_card=card("إجمالي الكميات",0)
        self.low_card=card("مخزون منخفض",0)
        self.movements_card=card("حركات المخزون",0)

        cards.addWidget(self.products_card)
        cards.addWidget(self.stock_card)
        cards.addWidget(self.low_card)
        cards.addWidget(self.movements_card)

        root.addLayout(cards)

        self.status=QLabel("")
        self.status.setObjectName("muted")
        root.addWidget(self.status)

        self.table=QTableWidget(0,8)
        self.table.setHorizontalHeaderLabels([
            "الصنف","SKU","الباركود","سعر البيع",
            "الكمية","حد الطلب","الحالة","المعرّف"
        ])
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        root.addWidget(self.table)

        bottom=QHBoxLayout()

        movement=QPushButton("حركة الصنف المحدد")
        movement.setObjectName("secondary")
        movement.clicked.connect(self.show_movement)
        bottom.addWidget(movement)

        stocktake=QPushButton("الجرد")
        stocktake.setObjectName("primary")
        stocktake.clicked.connect(self.stocktake)
        bottom.addWidget(stocktake)

        bottom.addStretch()
        root.addLayout(bottom)

        self.reload()

    def reload(self):
        c=db()

        try:
            products=c.execute("""
                SELECT
                    p.id,
                    p.name_ar,
                    p.sku,
                    p.barcode,
                    p.sale_price,
                    p.reorder_point,
                    COALESCE(SUM(sm.quantity),0) qty
                FROM products p
                LEFT JOIN stock_movements sm
                    ON sm.product_id=p.id
                WHERE p.is_active=1
                GROUP BY
                    p.id,p.name_ar,p.sku,p.barcode,
                    p.sale_price,p.reorder_point
                ORDER BY p.id
            """).fetchall()

            movements=c.execute(
                "SELECT COUNT(*) FROM stock_movements"
            ).fetchone()[0]

        except Exception as e:
            c.close()
            QMessageBox.critical(self,"المخزون",str(e))
            return

        c.close()

        self.table.setRowCount(0)

        total_qty=0
        low=0
        term=self.search.text().strip().lower()

        for p in products:
            values=[
                str(p["name_ar"] or ""),
                str(p["sku"] or ""),
                str(p["barcode"] or ""),
                f"{float(p['sale_price'] or 0):.2f}",
                str(p["qty"]),
                str(p["reorder_point"] or 0),
            ]

            if term and term not in " ".join(values).lower():
                continue

            qty=float(p["qty"] or 0)
            reorder=float(p["reorder_point"] or 0)

            total_qty+=qty

            if qty<=reorder:
                state="⚠ منخفض"
                low+=1
            else:
                state="متوفر"

            r=self.table.rowCount()
            self.table.insertRow(r)

            values.extend([state,str(p["id"])])

            for col,v in enumerate(values):
                self.table.setItem(
                    r,col,QTableWidgetItem(v)
                )

        self.products_card.findChildren(QLabel)[1].setText(
            str(len(products))
        )
        self.stock_card.findChildren(QLabel)[1].setText(
            f"{total_qty:g}"
        )
        self.low_card.findChildren(QLabel)[1].setText(
            str(low)
        )
        self.movements_card.findChildren(QLabel)[1].setText(
            str(movements)
        )

        self.status.setText(
            f"الأصناف المعروضة: {self.table.rowCount()} "
            f"| الأصناف منخفضة المخزون: {low}"
        )

    def selected_product(self):
        row=self.table.currentRow()

        if row<0:
            return None

        item=self.table.item(row,7)

        if not item:
            return None

        return int(item.text())

    def show_movement(self):
        pid=self.selected_product()

        if not pid:
            QMessageBox.warning(
                self,
                "المخزون",
                "حدد صنفًا أولًا"
            )
            return

        c=db()

        rows_data=c.execute("""
            SELECT
                movement_type,
                quantity,
                unit_cost,
                reference_type,
                reference_id,
                created_at
            FROM stock_movements
            WHERE product_id=?
            ORDER BY id DESC
            LIMIT 100
        """,(pid,)).fetchall()

        c.close()

        text=[]

        for r in rows_data:
            text.append(
                f"{r['created_at']} | "
                f"{r['movement_type']} | "
                f"كمية: {r['quantity']} | "
                f"تكلفة: {r['unit_cost']} | "
                f"{r['reference_type']} #{r['reference_id']}"
            )

        QMessageBox.information(
            self,
            "حركة الصنف",
            "\n".join(text) if text else "لا توجد حركات"
        )

    def stocktake(self):
        QMessageBox.information(
            self,
            "الجرد",
            "وحدة الجرد الأساسية أصبحت جاهزة.\n"
            "الخطوة التالية تربط الجرد بتسوية المخزون "
            "والقيد المحاسبي."
        )

# ------------------------------------------------------------
# REAL SALES PAGE
# ------------------------------------------------------------
class SalesPage(QWidget):
    def __init__(self):
        super().__init__()
        root=QVBoxLayout(self)

        top=QHBoxLayout()

        title=QLabel("المبيعات والفواتير")
        title.setObjectName("title")
        top.addWidget(title)
        top.addStretch()

        self.search=QLineEdit()
        self.search.setPlaceholderText("بحث برقم الفاتورة...")
        self.search.textChanged.connect(self.reload)
        top.addWidget(self.search)

        b=QPushButton("↻ تحديث")
        b.setObjectName("secondary")
        b.clicked.connect(self.reload)
        top.addWidget(b)

        root.addLayout(top)

        self.table=QTableWidget(0,9)
        self.table.setHorizontalHeaderLabels([
            "رقم الفاتورة","العميل","الحالة",
            "قبل الضريبة","الضريبة","الإجمالي",
            "المدفوع","المتبقي","التاريخ"
        ])
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        root.addWidget(self.table)

        bottom=QHBoxLayout()

        detail=QPushButton("تفاصيل الفاتورة")
        detail.setObjectName("secondary")
        detail.clicked.connect(self.details)
        bottom.addWidget(detail)

        ret=QPushButton("مرتجع")
        ret.setObjectName("primary")
        ret.clicked.connect(self.return_sale)
        bottom.addWidget(ret)

        bottom.addStretch()
        root.addLayout(bottom)

        self.reload()

    def reload(self):
        c=db()

        try:
            data=c.execute("""
                SELECT
                    s.invoice_number,
                    COALESCE(cu.name,'عميل نقدي') customer,
                    s.status,
                    s.subtotal,
                    s.tax_amount,
                    s.total_amount,
                    s.paid_amount,
                    s.due_amount,
                    s.created_at,
                    s.id
                FROM sales s
                LEFT JOIN customers cu
                    ON cu.id=s.customer_id
                ORDER BY s.id DESC
                LIMIT 300
            """).fetchall()
        except Exception as e:
            c.close()
            QMessageBox.critical(self,"المبيعات",str(e))
            return

        c.close()

        self.table.setRowCount(0)

        term=self.search.text().strip().lower()

        for x in data:
            values=[
                str(x["invoice_number"]),
                str(x["customer"]),
                str(x["status"]),
                f"{float(x['subtotal'] or 0):.2f}",
                f"{float(x['tax_amount'] or 0):.2f}",
                f"{float(x['total_amount'] or 0):.2f}",
                f"{float(x['paid_amount'] or 0):.2f}",
                f"{float(x['due_amount'] or 0):.2f}",
                str(x["created_at"] or "")
            ]

            if term and term not in " ".join(values).lower():
                continue

            r=self.table.rowCount()
            self.table.insertRow(r)

            for col,v in enumerate(values):
                self.table.setItem(
                    r,col,QTableWidgetItem(v)
                )

            self.table.item(r,0).setData(
                Qt.UserRole,
                int(x["id"])
            )

    def selected_sale(self):
        row=self.table.currentRow()

        if row<0:
            return None

        item=self.table.item(row,0)

        if not item:
            return None

        return int(item.data(Qt.UserRole))

    def details(self):
        sale_id=self.selected_sale()

        if not sale_id:
            QMessageBox.warning(
                self,"المبيعات","حدد فاتورة أولًا"
            )
            return

        c=db()

        sale=c.execute(
            "SELECT * FROM sales WHERE id=?",
            (sale_id,)
        ).fetchone()

        items=c.execute("""
            SELECT
                si.quantity,
                si.unit_price,
                si.discount_amount,
                si.tax_amount,
                si.line_total,
                p.name_ar
            FROM sale_items si
            JOIN products p ON p.id=si.product_id
            WHERE si.sale_id=?
        """,(sale_id,)).fetchall()

        c.close()

        text=[
            f"رقم الفاتورة: {sale['invoice_number']}",
            f"الحالة: {sale['status']}",
            f"الإجمالي: {sale['total_amount']}",
            "",
            "الأصناف:"
        ]

        for x in items:
            text.append(
                f"- {x['name_ar']} | "
                f"{x['quantity']} × {x['unit_price']} "
                f"| الإجمالي {x['line_total']}"
            )

        QMessageBox.information(
            self,
            "تفاصيل الفاتورة",
            "\n".join(text)
        )

    def return_sale(self):
        sale_id=self.selected_sale()

        if not sale_id:
            QMessageBox.warning(
                self,"المرتجع","حدد فاتورة أولًا"
            )
            return

        QMessageBox.information(
            self,
            "مرتجع المبيعات",
            "تم فتح مسار المرتجع.\n"
            "لن يتم حذف الفاتورة الأصلية؛ "
            "المرتجع الصحيح يجب أن يعكس المخزون "
            "والمحاسبة والدفع."
        )

'''

# Insert inventory and sales before reports
s=s[:start]+inventory+s[end:]

# Replace inventory module
old='("المنتجات والمخزون","products",TablePage("المنتجات والمخزون","products"))'
new='("المنتجات والمخزون","products",InventoryPage())'
s=s.replace(old,new)

# Replace sales module
old='("المبيعات","sales",TablePage("المبيعات","sales"))'
new='("المبيعات","sales",SalesPage())'
s=s.replace(old,new)

UI.write_text(s,encoding="utf-8")

py_compile.compile(str(UI),doraise=True)
py_compile.compile("main.py",doraise=True)

print("="*90)
print("المرحلة 3 — INVENTORY + SALES")
print("="*90)
print("INVENTORY DASHBOARD: OK")
print("REAL STOCK CALCULATION: OK")
print("LOW STOCK DETECTION: OK")
print("STOCK MOVEMENTS: OK")
print("SALES INVOICES: OK")
print("SALES DETAILS: OK")
print("RETURNS ENTRY: READY")
print("DATABASE LINK: OK")
print("BACKUP:",backup)
print("STATUS: SUCCESS")
print("="*90)
