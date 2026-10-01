from app.ui.theme import APP_STYLE

from pathlib import Path
import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,
    QTableWidget,QTableWidgetItem,QTabWidget,QLineEdit,
    QMessageBox,QHeaderView
)

class OperationsCenter(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setStyleSheet(APP_STYLE)
        self.setWindowTitle("مركز عمليات نظام القرطاسية")
        self.resize(1250,750)
        self.setLayoutDirection(Qt.RightToLeft)

        self.db=Path(__file__).resolve().parents[2] / "database" / "nizam_alqirtasiyah.db"

        root=QVBoxLayout(self)

        title=QLabel("نظام القرطاسية — مركز العمليات")
        title.setStyleSheet(
            "font-size:26px;font-weight:bold;padding:15px;"
        )
        root.addWidget(title)

        self.tabs=QTabWidget()
        root.addWidget(self.tabs)

        self.build_dashboard()
        self.build_products()
        self.build_customers()
        self.build_suppliers()
        self.build_sales()
        self.build_purchases()
        self.build_stock()
        self.build_cash()
        self.build_reports()

        self.refresh_all()

    def query(self,sql,args=()):
        con=sqlite3.connect(self.db)
        con.row_factory=sqlite3.Row
        try:
            return [dict(x) for x in con.execute(sql,args).fetchall()]
        finally:
            con.close()

    def scalar(self,sql,args=()):
        con=sqlite3.connect(self.db)
        try:
            x=con.execute(sql,args).fetchone()
            return x[0] if x else 0
        finally:
            con.close()

    def build_dashboard(self):
        w=QWidget()
        l=QVBoxLayout(w)
        self.dashboard=QLabel()
        self.dashboard.setStyleSheet(
            "font-size:20px;padding:25px;line-height:2;"
        )
        l.addWidget(self.dashboard)

        b=QPushButton("تحديث لوحة التحكم")
        b.clicked.connect(self.refresh_dashboard)
        l.addWidget(b)

        self.tabs.addTab(w,"لوحة التحكم")

    def build_products(self):
        w=QWidget()
        l=QVBoxLayout(w)
        self.product_search=QLineEdit()
        self.product_search.setPlaceholderText("بحث بالاسم أو SKU...")
        self.product_search.textChanged.connect(self.refresh_products)
        l.addWidget(self.product_search)

        self.products=QTableWidget(0,5)
        self.products.setHorizontalHeaderLabels(
            ["الاسم","SKU","سعر البيع","التكلفة","نقطة إعادة الطلب"]
        )
        self.products.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        l.addWidget(self.products)
        self.tabs.addTab(w,"المنتجات")

    def build_customers(self):
        w=QWidget()
        l=QVBoxLayout(w)
        self.customers=QTableWidget(0,4)
        self.customers.setHorizontalHeaderLabels(
            ["الاسم","الكود","الهاتف","الرصيد"]
        )
        self.customers.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        l.addWidget(self.customers)
        self.tabs.addTab(w,"العملاء")

    def build_suppliers(self):
        w=QWidget()
        l=QVBoxLayout(w)
        self.suppliers=QTableWidget(0,4)
        self.suppliers.setHorizontalHeaderLabels(
            ["المورد","الكود","الهاتف","الرصيد"]
        )
        self.suppliers.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        l.addWidget(self.suppliers)
        self.tabs.addTab(w,"الموردون")

    def build_sales(self):
        w=QWidget()
        l=QVBoxLayout(w)
        self.sales=QTableWidget(0,5)
        self.sales.setHorizontalHeaderLabels(
            ["الفاتورة","التاريخ","الإجمالي","المدفوع","المتبقي"]
        )
        self.sales.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        l.addWidget(self.sales)
        self.tabs.addTab(w,"المبيعات")

    def build_purchases(self):
        w=QWidget()
        l=QVBoxLayout(w)
        self.purchases=QTableWidget(0,5)
        self.purchases.setHorizontalHeaderLabels(
            ["الفاتورة","التاريخ","الإجمالي","المدفوع","المتبقي"]
        )
        self.purchases.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        l.addWidget(self.purchases)
        self.tabs.addTab(w,"المشتريات")

    def build_stock(self):
        w=QWidget()
        l=QVBoxLayout(w)
        self.stock=QTableWidget(0,5)
        self.stock.setHorizontalHeaderLabels(
            ["المنتج","نوع الحركة","الكمية","التكلفة","التاريخ"]
        )
        self.stock.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        l.addWidget(self.stock)
        self.tabs.addTab(w,"المخزون")

    def build_cash(self):
        w=QWidget()
        l=QVBoxLayout(w)
        self.cash=QTableWidget(0,4)
        self.cash.setHorizontalHeaderLabels(
            ["النوع","المبلغ","المرجع","التاريخ"]
        )
        self.cash.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        l.addWidget(self.cash)
        self.tabs.addTab(w,"الخزينة")

    def build_reports(self):
        w=QWidget()
        l=QVBoxLayout(w)
        self.reports=QLabel()
        self.reports.setStyleSheet("font-size:18px;padding:20px;")
        l.addWidget(self.reports)

        b=QPushButton("تحديث التقارير")
        b.clicked.connect(self.refresh_reports)
        l.addWidget(b)
        self.tabs.addTab(w,"التقارير")

    def refresh_dashboard(self):
        products=self.scalar("SELECT COUNT(*) FROM products")
        customers=self.scalar("SELECT COUNT(*) FROM customers")
        suppliers=self.scalar("SELECT COUNT(*) FROM suppliers")
        sales=self.scalar("SELECT COUNT(*) FROM sales")
        purchases=self.scalar("SELECT COUNT(*) FROM purchase_invoices")
        stock=self.scalar("SELECT COUNT(*) FROM stock_movements")

        sales_total=self.scalar(
            "SELECT COALESCE(SUM(total_amount),0) FROM sales"
        )
        purchase_total=self.scalar(
            "SELECT COALESCE(SUM(total_amount),0) FROM purchase_invoices"
        )

        self.dashboard.setText(
            f"المنتجات: {products}\n"
            f"العملاء: {customers}\n"
            f"الموردون: {suppliers}\n"
            f"فواتير المبيعات: {sales}\n"
            f"فواتير المشتريات: {purchases}\n"
            f"حركات المخزون: {stock}\n\n"
            f"إجمالي المبيعات: {sales_total:.2f}\n"
            f"إجمالي المشتريات: {purchase_total:.2f}"
        )

    def fill(self,table,rows,keys):
        table.setRowCount(0)
        for row in rows:
            r=table.rowCount()
            table.insertRow(r)
            for c,k in enumerate(keys):
                v=row.get(k,"")
                if v is None:
                    v=""
                table.setItem(r,c,QTableWidgetItem(str(v)))

    def refresh_products(self):
        q=self.product_search.text().strip()
        rows=self.query("""
            SELECT name_ar,sku,sale_price,cost_price,reorder_point
            FROM products
            WHERE is_active=1
            AND (name_ar LIKE ? OR sku LIKE ?)
            ORDER BY id DESC
        """,(f"%{q}%",f"%{q}%"))
        self.fill(
            self.products,rows,
            ["name_ar","sku","sale_price","cost_price","reorder_point"]
        )

    def refresh_customers(self):
        rows=self.query("""
            SELECT name,customer_code,phone,current_balance
            FROM customers ORDER BY id DESC
        """)
        self.fill(
            self.customers,rows,
            ["name","customer_code","phone","current_balance"]
        )

    def refresh_suppliers(self):
        rows=self.query("""
            SELECT name,supplier_code,phone,current_balance
            FROM suppliers ORDER BY id DESC
        """)
        self.fill(
            self.suppliers,rows,
            ["name","supplier_code","phone","current_balance"]
        )

    def refresh_sales(self):
        rows=self.query("""
            SELECT invoice_number,created_at,total_amount,
                   paid_amount,due_amount
            FROM sales ORDER BY id DESC LIMIT 200
        """)
        self.fill(
            self.sales,rows,
            ["invoice_number","created_at","total_amount",
             "paid_amount","due_amount"]
        )

    def refresh_purchases(self):
        rows=self.query("""
            SELECT invoice_number,invoice_date,total_amount,
                   paid_amount,due_amount
            FROM purchase_invoices ORDER BY id DESC LIMIT 200
        """)
        self.fill(
            self.purchases,rows,
            ["invoice_number","invoice_date","total_amount",
             "paid_amount","due_amount"]
        )

    def refresh_stock(self):
        rows=self.query("""
            SELECT p.name_ar,s.movement_type,s.quantity,
                   s.unit_cost,s.created_at
            FROM stock_movements s
            LEFT JOIN products p ON p.id=s.product_id
            ORDER BY s.id DESC LIMIT 300
        """)
        self.fill(
            self.stock,rows,
            ["name_ar","movement_type","quantity",
             "unit_cost","created_at"]
        )

    def refresh_cash(self):
        rows=self.query("""
            SELECT transaction_type,amount,reference_number,created_at
            FROM cash_transactions
            ORDER BY id DESC LIMIT 200
        """)
        self.fill(
            self.cash,rows,
            ["transaction_type","amount",
             "reference_number","created_at"]
        )

    def refresh_reports(self):
        sales=self.scalar(
            "SELECT COALESCE(SUM(total_amount),0) FROM sales"
        )
        purchases=self.scalar(
            "SELECT COALESCE(SUM(total_amount),0) FROM purchase_invoices"
        )
        paid=self.scalar(
            "SELECT COALESCE(SUM(paid_amount),0) FROM sales"
        )
        due=self.scalar(
            "SELECT COALESCE(SUM(due_amount),0) FROM sales"
        )
        self.reports.setText(
            f"تقرير المبيعات: {sales:.2f}\n"
            f"تقرير المشتريات: {purchases:.2f}\n"
            f"المدفوع من العملاء: {paid:.2f}\n"
            f"المتبقي على العملاء: {due:.2f}"
        )

    def refresh_all(self):
        self.refresh_dashboard()
        self.refresh_products()
        self.refresh_customers()
        self.refresh_suppliers()
        self.refresh_sales()
        self.refresh_purchases()
        self.refresh_stock()
        self.refresh_cash()
        self.refresh_reports()
