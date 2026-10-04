from datetime import date, timedelta
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QDateEdit,QTableWidget,QTableWidgetItem,QHeaderView,QGridLayout
from sqlalchemy import text
from app.database.connection import get_session
from app.ui.theme import APP_STYLE
from app.ui.dashboard_widgets import DashboardCard, KpiCard, TrendChart

class AnalyticsWindow(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setStyleSheet(APP_STYLE); self.setWindowTitle("التحليلات"); self.setMinimumSize(1250,780); self.setLayoutDirection(Qt.RightToLeft)
        root=QVBoxLayout(self); root.setContentsMargins(18,18,18,18); root.setSpacing(12)
        head=QHBoxLayout(); title=QLabel("مركز ذكاء الأعمال والتحليلات"); title.setObjectName("SectionTitle"); head.addWidget(title); head.addStretch()
        self.frm=QDateEdit(); self.frm.setCalendarPopup(True); self.frm.setDate(date.today()-timedelta(days=29))
        self.to=QDateEdit(); self.to.setCalendarPopup(True); self.to.setDate(date.today())
        view=QPushButton("تحديث التحليل"); view.setObjectName("Primary"); view.clicked.connect(self.load)
        head.addWidget(QLabel("من:")); head.addWidget(self.frm); head.addWidget(QLabel("إلى:")); head.addWidget(self.to); head.addWidget(view); root.addLayout(head)
        self.kpis=QGridLayout(); self.kpis.setSpacing(10); root.addLayout(self.kpis)
        charts=QHBoxLayout(); charts.setSpacing(10)
        self.sales_chart=TrendChart(); self.sales_card=DashboardCard("اتجاه المبيعات والمشتريات","الفترة المحددة"); self.sales_card.layout.addWidget(self.sales_chart)
        self.expense_chart=TrendChart(bar=True); self.expense_card=DashboardCard("المصروفات التشغيلية","حسب الشهر"); self.expense_card.layout.addWidget(self.expense_chart)
        charts.addWidget(self.sales_card,2); charts.addWidget(self.expense_card,1); root.addLayout(charts,1)
        self.table=QTableWidget(0,5); self.table.setHorizontalHeaderLabels(["المؤشر","العدد/الكمية","القيمة","المتوسط","ملاحظات"]); self.table.horizontalHeader().setSectionResizeMode(4,QHeaderView.Stretch); self.table.setAlternatingRowColors(True); self.table.setSortingEnabled(True); root.addWidget(self.table,1)
        self.load()

    def _kpi(self,title,value,caption,icon,accent):
        card=KpiCard(title,value,caption,icon,accent); return card

    def load(self):
        f=self.frm.date().toString("yyyy-MM-dd"); t=self.to.date().toString("yyyy-MM-dd")
        with get_session() as s:
            sales=s.execute(text("SELECT COUNT(*),COALESCE(SUM(total_amount),0),COALESCE(SUM(paid_amount),0) FROM sales WHERE status IN ('POSTED','completed') AND date(created_at) BETWEEN :f AND :t"),{"f":f,"t":t}).one()
            purchases=s.execute(text("SELECT COUNT(*),COALESCE(SUM(total_amount),0) FROM purchase_invoices WHERE date(invoice_date) BETWEEN :f AND :t"),{"f":f,"t":t}).one()
            stock=s.execute(text("SELECT COUNT(*),COALESCE(SUM(quantity*average_cost),0) FROM stock_balances")).one()
            customers=s.execute(text("SELECT COUNT(*),COALESCE(SUM(current_balance),0) FROM customers")).one()
            top=s.execute(text("SELECT p.name_ar,COALESCE(SUM(si.quantity),0),COALESCE(SUM(si.line_total),0) FROM sale_items si JOIN sales s ON s.id=si.sale_id JOIN products p ON p.id=si.product_id WHERE s.status IN ('POSTED','completed') AND date(s.created_at) BETWEEN :f AND :t GROUP BY p.id,p.name_ar ORDER BY SUM(si.quantity) DESC LIMIT 5"),{"f":f,"t":t}).all()
        while self.kpis.count():
            item=self.kpis.takeAt(0); w=item.widget()
            if w: w.deleteLater()
        values=[
            self._kpi("المبيعات",f"{float(sales[1]):,.2f}","إجمالي الفترة","↗","#2563eb"),
            self._kpi("المشتريات",f"{float(purchases[1]):,.2f}","إجمالي الفترة","↘","#7c3aed"),
            self._kpi("قيمة المخزون",f"{float(stock[1]):,.2f}","بالتكلفة المتوسطة","▣","#0f766e"),
            self._kpi("أرصدة العملاء",f"{float(customers[1]):,.2f}","الأرصدة الحالية","◉","#d97706"),
        ]
        for i,w in enumerate(values): self.kpis.addWidget(w,0,i)
        rows=[
            ("المبيعات",sales[0],sales[1],float(sales[1])/(sales[0] or 1),f"المدفوع: {float(sales[2]):,.2f}"),
            ("المشتريات",purchases[0],purchases[1],float(purchases[1])/(purchases[0] or 1),"إجمالي فواتير الشراء"),
            ("قيمة المخزون",stock[0],stock[1],0,"القيمة بالتكلفة المتوسطة"),
            ("أرصدة العملاء",customers[0],customers[1],0,"الرصيد الحالي"),
        ]
        for name,qty,value in top: rows.append((f"الأكثر مبيعًا: {name}",qty,value,0,"حسب الكمية"))
        self.table.setRowCount(0)
        for vals in rows:
            r=self.table.rowCount(); self.table.insertRow(r)
            for c,v in enumerate(vals): self.table.setItem(r,c,QTableWidgetItem(f"{v:,.2f}" if isinstance(v,float) else str(v)))
        # المخطط اليومي يُقرأ من قاعدة البيانات داخل جلسة مستقلة حتى لا يبقى أي اتصال مفتوح.
        with get_session() as s:
            sales_rows=s.execute(text("SELECT date(created_at),COALESCE(SUM(total_amount),0) FROM sales WHERE status IN ('POSTED','completed') AND date(created_at) BETWEEN :f AND :t GROUP BY date(created_at) ORDER BY date(created_at)"),{"f":f,"t":t}).all()
            expense_exists=s.execute(text("SELECT 1 FROM sqlite_master WHERE type='table' AND name='expenses'")).scalar()
            expense_rows=s.execute(text("SELECT date(expense_date),COALESCE(SUM(amount),0) FROM expenses WHERE date(expense_date) BETWEEN :f AND :t GROUP BY date(expense_date) ORDER BY date(expense_date)"),{"f":f,"t":t}).all() if expense_exists else []
        labels=[str(x[0])[5:] for x in sales_rows][-14:]
        vals=[float(x[1] or 0) for x in sales_rows][-14:]
        emap={str(x[0]):float(x[1] or 0) for x in expense_rows}
        evals=[emap.get(str(x[0]),0.0) for x in sales_rows][-14:]
        self.sales_chart.set_data(labels,[{"name":"المبيعات","values":vals,"color":"#2563eb"}])
        self.expense_chart.set_data(labels,[{"name":"المصروفات","values":evals,"color":"#d97706"}])
