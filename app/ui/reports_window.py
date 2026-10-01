from datetime import date,timedelta
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QComboBox,QDateEdit,QLineEdit,QMessageBox
from sqlalchemy import text
from app.database.connection import get_session
from app.services.report_export_service import ReportExportService
from app.ui.theme import APP_STYLE

REPORTS=[
("sales","مبيعات الفترة"),("sales_product","المبيعات حسب الصنف"),("sales_customer","المبيعات حسب العميل"),
("purchases","مشتريات الفترة"),("purchases_supplier","المشتريات حسب المورد"),("purchases_unpaid","المشتريات غير المسددة"),
("stock","المخزون الحالي"),("low_stock","الأصناف منخفضة المخزون"),("stock_movement","حركة المخزون"),
("customer_balance","كشف أرصدة العملاء"),("supplier_balance","كشف أرصدة الموردين"),("journal","دفتر اليومية"),
("ledger","دفتر الأستاذ"),("trial","ميزان المراجعة"),("income","قائمة الدخل"),("balance","الميزانية"),
("cashflow","التدفق النقدي"),("cash","حركة الصناديق"),("bank","حركة البنوك"),("tax","الضريبة"),
("expenses","المصروفات")]

class ReportsWindow(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent); self.setStyleSheet(APP_STYLE); self.setWindowTitle("التقارير"); self.setMinimumSize(1250,760); self.setLayoutDirection(Qt.RightToLeft)
        root=QVBoxLayout(self); h=QHBoxLayout(); t=QLabel("التقارير"); t.setObjectName("SectionTitle"); h.addWidget(t); h.addStretch()
        self.report=QComboBox(); [self.report.addItem(n,k) for k,n in REPORTS]; self.report.currentIndexChanged.connect(self.load); h.addWidget(self.report)
        self.frm=QDateEdit(); self.frm.setCalendarPopup(True); self.frm.setDate(date.today()-timedelta(days=29)); self.to=QDateEdit(); self.to.setCalendarPopup(True); self.to.setDate(date.today())
        h.addWidget(QLabel("من:")); h.addWidget(self.frm); h.addWidget(QLabel("إلى:")); h.addWidget(self.to)
        root.addLayout(h)
        f=QHBoxLayout()
        for label,attr,ph in [("الفرع","branch","رقم الفرع"),("المستودع","warehouse","رقم المستودع"),("العميل","customer","رقم العميل"),("المورد","supplier","رقم المورد"),("الصنف","product","رقم الصنف"),("التصنيف","category","رقم التصنيف"),("الحالة","status","الحالة")]:
            w=QLineEdit(); w.setPlaceholderText(ph); setattr(self,attr,w); w.textChanged.connect(self.load); f.addWidget(w)
        root.addLayout(f)
        a=QHBoxLayout()
        for cap,fn,obj in [("عرض",self.load,"Primary"),("Excel",self.export_excel,"Success"),("PDF",self.export_pdf,"Warning")]:
            b=QPushButton(cap); b.setObjectName(obj); b.clicked.connect(fn); a.addWidget(b)
        a.addStretch(); root.addLayout(a)
        self.table=QTableWidget(0,1); self.table.setAlternatingRowColors(True); self.table.setSelectionBehavior(QAbstractItemView.SelectRows); self.table.setEditTriggers(QAbstractItemView.NoEditTriggers); self.table.horizontalHeader().setStretchLastSection(True); root.addWidget(self.table,1)
        self.status=QLabel("جاهز"); root.addWidget(self.status); self.load()
    def _params(self):
        return {"f":self.frm.date().toString("yyyy-MM-dd"),"t":self.to.date().toString("yyyy-MM-dd")}
    def load(self,*_):
        k=self.report.currentData(); p=self._params(); f,t=p["f"],p["t"]; rows=[]; headers=[]
        with get_session() as s:
            if k=="sales":
                headers=["الفواتير","الإجمالي","المدفوع","المتبقي"]; q="""SELECT COUNT(*),COALESCE(SUM(total_amount),0),COALESCE(SUM(paid_amount),0),COALESCE(SUM(due_amount),0) FROM sales WHERE status='POSTED' AND date(created_at) BETWEEN :f AND :t"""
                if self.customer.text().strip(): q+=" AND customer_id=:customer"; p["customer"]=int(self.customer.text())
                r=s.execute(text(q),p).one(); rows=[r]
            elif k=="sales_product":
                headers=["الصنف","الكمية","المبيعات","الخصم"]; q="""SELECT p.name_ar,SUM(si.quantity),SUM(si.line_total),SUM(si.discount_amount) FROM sale_items si JOIN sales s ON s.id=si.sale_id JOIN products p ON p.id=si.product_id WHERE s.status='POSTED' AND date(s.created_at) BETWEEN :f AND :t"""
                if self.product.text().strip(): q+=" AND p.id=:product"; p["product"]=int(self.product.text())
                if self.category.text().strip(): q+=" AND p.category_id=:category"; p["category"]=int(self.category.text())
                q+=" GROUP BY p.id,p.name_ar ORDER BY SUM(si.line_total) DESC"; rows=s.execute(text(q),p).all()
            elif k=="sales_customer":
                headers=["العميل","الفواتير","المبيعات","المدفوع","المتبقي"]; q="""SELECT COALESCE(c.name,'نقدي'),COUNT(s.id),COALESCE(SUM(s.total_amount),0),COALESCE(SUM(s.paid_amount),0),COALESCE(SUM(s.due_amount),0) FROM sales s LEFT JOIN customers c ON c.id=s.customer_id WHERE s.status='POSTED' AND date(s.created_at) BETWEEN :f AND :t"""
                if self.customer.text().strip(): q+=" AND s.customer_id=:customer"; p["customer"]=int(self.customer.text())
                q+=" GROUP BY c.id,c.name ORDER BY SUM(s.total_amount) DESC"; rows=s.execute(text(q),p).all()
            elif k=="purchases":
                headers=["الفواتير","الإجمالي","المدفوع","المتبقي"]; q="SELECT COUNT(*),COALESCE(SUM(total_amount),0),COALESCE(SUM(paid_amount),0),COALESCE(SUM(due_amount),0) FROM purchase_invoices WHERE date(invoice_date) BETWEEN :f AND :t"; rows=[s.execute(text(q),p).one()]
            elif k in {"purchases_supplier","purchases_unpaid"}:
                headers=["المورد","الفواتير","الإجمالي","المدفوع","المتبقي"]; q="""SELECT COALESCE(sp.name,'غير محدد'),COUNT(pi.id),COALESCE(SUM(pi.total_amount),0),COALESCE(SUM(pi.paid_amount),0),COALESCE(SUM(pi.due_amount),0) FROM purchase_invoices pi LEFT JOIN suppliers sp ON sp.id=pi.supplier_id WHERE date(pi.invoice_date) BETWEEN :f AND :t"""
                if k=="purchases_unpaid": q+=" AND COALESCE(pi.due_amount,0)>0"
                if self.supplier.text().strip(): q+=" AND pi.supplier_id=:supplier"; p["supplier"]=int(self.supplier.text())
                q+=" GROUP BY sp.id,sp.name ORDER BY SUM(pi.total_amount) DESC"; rows=s.execute(text(q),p).all()
            elif k=="stock":
                headers=["الصنف","المستودع","الكمية","المتاح","التكلفة المتوسطة","القيمة"]; rows=s.execute(text("""SELECT p.name_ar,w.name,st.quantity,st.available_quantity,st.average_cost,st.quantity*st.average_cost FROM stock st JOIN products p ON p.id=st.product_id JOIN warehouses w ON w.id=st.warehouse_id WHERE (:product='' OR st.product_id=:product) AND (:warehouse='' OR st.warehouse_id=:warehouse) ORDER BY p.name_ar"""),{"product":self.product.text().strip(),"warehouse":self.warehouse.text().strip()}).all()
            elif k=="low_stock":
                headers=["الصنف","الباركود","المتاح","الحد الأدنى"]; rows=s.execute(text("""SELECT p.name_ar,p.sku,COALESCE(st.available_quantity,0),COALESCE(NULLIF(p.reorder_point,0),p.min_stock,0) FROM products p LEFT JOIN stock st ON st.product_id=p.id WHERE p.is_active=1 AND COALESCE(st.available_quantity,0)<=COALESCE(NULLIF(p.reorder_point,0),p.min_stock,0) ORDER BY COALESCE(st.available_quantity,0),p.name_ar""")).all()
            elif k=="stock_movement":
                headers=["التاريخ","الصنف","المستودع","الحركة","الكمية","التكلفة","المستند"]; q="""SELECT sm.created_at,p.name_ar,w.name,sm.movement_type,sm.quantity,sm.unit_cost,sm.reference_type FROM stock_movements sm JOIN products p ON p.id=sm.product_id JOIN warehouses w ON w.id=sm.warehouse_id WHERE date(sm.created_at) BETWEEN :f AND :t"""; q+=" AND (:product='' OR sm.product_id=:product) AND (:warehouse='' OR sm.warehouse_id=:warehouse) ORDER BY sm.id DESC"; p.update({"product":self.product.text().strip(),"warehouse":self.warehouse.text().strip()}); rows=s.execute(text(q),p).all()
            elif k=="customer_balance":
                headers=["العميل","رقم العميل","الرصيد","حد الائتمان"]; q="SELECT name,customer_code,current_balance,credit_limit FROM customers WHERE (:customer='' OR id=:customer) ORDER BY name"; rows=s.execute(text(q),{"customer":self.customer.text().strip()}).all()
            elif k=="supplier_balance":
                headers=["المورد","رقم المورد","الرصيد","حد الائتمان"]; q="SELECT name,supplier_code,current_balance,credit_limit FROM suppliers WHERE (:supplier='' OR id=:supplier) ORDER BY name"; rows=s.execute(text(q),{"supplier":self.supplier.text().strip()}).all()
            elif k=="journal":
                headers=["التاريخ","رقم القيد","البيان","الحالة"]; rows=s.execute(text("SELECT entry_date,entry_number,description,status FROM journal_entries WHERE date(entry_date) BETWEEN :f AND :t ORDER BY id DESC"),p).all()
            elif k=="ledger":
                headers=["الحساب","رقم الحساب","مدين","دائن","الرصيد"]; rows=s.execute(text("""SELECT a.account_name,a.account_code,COALESCE(SUM(jl.debit),0),COALESCE(SUM(jl.credit),0),COALESCE(SUM(jl.debit-jl.credit),0) FROM journal_entry_lines jl JOIN journal_entries je ON je.id=jl.journal_entry_id JOIN accounts a ON a.id=jl.account_id WHERE date(je.entry_date) BETWEEN :f AND :t AND je.status='POSTED' GROUP BY a.id,a.account_name,a.account_code ORDER BY a.account_code"""),p).all()
            elif k=="trial":
                headers=["رقم الحساب","الحساب","مدين","دائن"]; rows=s.execute(text("""SELECT a.account_code,a.account_name,COALESCE(SUM(jl.debit),0),COALESCE(SUM(jl.credit),0) FROM journal_entry_lines jl JOIN journal_entries je ON je.id=jl.journal_entry_id JOIN accounts a ON a.id=jl.account_id WHERE je.status='POSTED' AND date(je.entry_date) BETWEEN :f AND :t GROUP BY a.id,a.account_code,a.account_name ORDER BY a.account_code"""),p).all()
            elif k in {"income","balance"}:
                headers=["الحساب","الرصيد"]; condition="REVENUE","ASSET"
                typ=condition[0] if k=="income" else condition[1]
                rows=s.execute(text("""SELECT a.account_name,COALESCE(SUM(jl.credit-jl.debit),0) FROM journal_entry_lines jl JOIN journal_entries je ON je.id=jl.journal_entry_id JOIN accounts a ON a.id=jl.account_id WHERE je.status='POSTED' AND a.account_type=:typ AND date(je.entry_date) BETWEEN :f AND :t GROUP BY a.id,a.account_name ORDER BY a.account_code"""),{**p,"typ":typ}).all()
            elif k=="cashflow":
                headers=["النوع","القيمة"]; rows=s.execute(text("""SELECT 'مبيعات نقدية',COALESCE(SUM(sp.amount),0) FROM sale_payments sp JOIN sales s ON s.id=sp.sale_id WHERE date(s.created_at) BETWEEN :f AND :t UNION ALL SELECT 'مدفوعات شراء',COALESCE(SUM(pi.paid_amount),0) FROM purchase_invoices pi WHERE date(pi.invoice_date) BETWEEN :f AND :t UNION ALL SELECT 'مصروفات',COALESCE(SUM(amount),0) FROM expenses WHERE date(expense_date) BETWEEN :f AND :t"""),p).all()
            elif k=="cash":
                headers=["التاريخ","المستند","الحركة","المبلغ"]; rows=s.execute(text("SELECT created_at,document_number,movement_type,amount FROM treasury_movements WHERE date(created_at) BETWEEN :f AND :t ORDER BY id DESC"),p).all()
            elif k=="bank":
                headers=["التاريخ","الحساب","النوع","المبلغ","المرجع"]; rows=s.execute(text("SELECT bt.created_at,ba.account_name,bt.transaction_type,bt.amount,bt.reference_number FROM bank_transactions bt JOIN bank_accounts ba ON ba.id=bt.bank_account_id WHERE date(bt.created_at) BETWEEN :f AND :t ORDER BY bt.id DESC"),p).all()
            elif k=="tax":
                headers=["الفواتير","الضريبة"]; rows=[s.execute(text("SELECT COUNT(*),COALESCE(SUM(tax_amount),0) FROM sales WHERE status='POSTED' AND date(created_at) BETWEEN :f AND :t"),p).one()]
            elif k=="expenses":
                headers=["التاريخ","الرقم","التصنيف","البيان","المبلغ","طريقة الدفع"]; rows=s.execute(text("SELECT expense_date,expense_number,category,description,amount,payment_method FROM expenses WHERE date(expense_date) BETWEEN :f AND :t ORDER BY id DESC"),p).all()
        self.headers=headers; self.rows=[tuple(x) for x in rows]; self.table.setColumnCount(len(headers)); self.table.setHorizontalHeaderLabels(headers); self.table.setRowCount(0)
        for vals in self.rows:
            r=self.table.rowCount(); self.table.insertRow(r)
            for c,v in enumerate(vals): self.table.setItem(r,c,QTableWidgetItem("" if v is None else str(v)))
        self.status.setText(f"{self.report.currentText()} — {len(self.rows):,} سجل")
    def export_excel(self):
        try: path=ReportExportService.to_excel("تقرير_"+self.report.currentText(),self.headers,self.rows); QMessageBox.information(self,"التصدير",f"تم إنشاء ملف Excel:\n{path}")
        except Exception as e: QMessageBox.critical(self,"فشل التصدير",str(e))
    def export_pdf(self):
        try: path=ReportExportService.to_pdf("تقرير_"+self.report.currentText(),self.headers,self.rows); QMessageBox.information(self,"التصدير",f"تم إنشاء ملف PDF:\n{path}")
        except Exception as e: QMessageBox.critical(self,"فشل التصدير",str(e))
