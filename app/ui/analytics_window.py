from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QDateEdit,QTableWidget,QTableWidgetItem,QHeaderView
from datetime import date,timedelta
from sqlalchemy import text
from app.database.connection import get_session
from app.ui.theme import APP_STYLE

class AnalyticsWindow(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent); self.setStyleSheet(APP_STYLE); self.setWindowTitle("التحليلات"); self.setMinimumSize(1150,700); self.setLayoutDirection(Qt.RightToLeft)
        root=QVBoxLayout(self); h=QHBoxLayout(); t=QLabel("التحليلات التشغيلية"); t.setObjectName("SectionTitle"); h.addWidget(t); h.addStretch()
        self.frm=QDateEdit(); self.frm.setCalendarPopup(True); self.frm.setDate(date.today()-timedelta(days=29))
        self.to=QDateEdit(); self.to.setCalendarPopup(True); self.to.setDate(date.today())
        view=QPushButton("عرض"); view.setObjectName("Primary"); view.clicked.connect(self.load)
        h.addWidget(QLabel("من:")); h.addWidget(self.frm); h.addWidget(QLabel("إلى:")); h.addWidget(self.to); h.addWidget(view); root.addLayout(h)
        self.table=QTableWidget(0,5); self.table.setHorizontalHeaderLabels(["المؤشر","العدد/الكمية","القيمة","المتوسط","ملاحظات"]); self.table.horizontalHeader().setSectionResizeMode(4,QHeaderView.Stretch); self.table.setAlternatingRowColors(True); root.addWidget(self.table,1); self.load()
    def load(self):
        f=self.frm.date().toString("yyyy-MM-dd"); t=self.to.date().toString("yyyy-MM-dd")
        with get_session() as s:
            sales=s.execute(text("SELECT COUNT(*),COALESCE(SUM(total_amount),0),COALESCE(SUM(paid_amount),0) FROM sales WHERE status='POSTED' AND date(created_at) BETWEEN :f AND :t"),{"f":f,"t":t}).one()
            purchases=s.execute(text("SELECT COUNT(*),COALESCE(SUM(total_amount),0) FROM purchase_invoices WHERE date(invoice_date) BETWEEN :f AND :t"),{"f":f,"t":t}).one()
            top=s.execute(text("SELECT p.name_ar,COALESCE(SUM(si.quantity),0),COALESCE(SUM(si.line_total),0) FROM sale_items si JOIN sales s ON s.id=si.sale_id JOIN products p ON p.id=si.product_id WHERE s.status='POSTED' AND date(s.created_at) BETWEEN :f AND :t GROUP BY p.id,p.name_ar ORDER BY SUM(si.quantity) DESC LIMIT 5"),{"f":f,"t":t}).all()
            stock=s.execute(text("SELECT COUNT(*),COALESCE(SUM(quantity*average_cost),0) FROM stock_balances")).one()
            customers=s.execute(text("SELECT COUNT(*),COALESCE(SUM(current_balance),0) FROM customers")).one()
        rows=[
            ("المبيعات",sales[0],sales[1],(float(sales[1])/(sales[0] or 1)),f"المدفوع: {float(sales[2]):,.2f}"),
            ("المشتريات",purchases[0],purchases[1],(float(purchases[1])/(purchases[0] or 1)),"إجمالي فواتير الشراء"),
            ("قيمة المخزون",stock[0],stock[1],0,"القيمة بالتكلفة المتوسطة"),
            ("أرصدة العملاء",customers[0],customers[1],0,"الرصيد الحالي"),
        ]
        for n,q,v,a,m in top: rows.append((f"الأكثر مبيعًا: {n}",q,v,0,"حسب الكمية"))
        self.table.setRowCount(0)
        for vals in rows:
            r=self.table.rowCount(); self.table.insertRow(r)
            for c,v in enumerate(vals): self.table.setItem(r,c,QTableWidgetItem(f"{v:,.2f}" if isinstance(v,float) else str(v)))
