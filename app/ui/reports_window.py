from datetime import date, timedelta
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QComboBox,QDateEdit,QLineEdit,QMessageBox
from sqlalchemy import text
from app.database.connection import get_session
from app.services.report_export_service import ReportExportService
from app.ui.theme import APP_STYLE

REPORTS=[
("sales_day","مبيعات اليوم"),("sales_period","مبيعات الفترة"),("sales_product","المبيعات حسب الصنف"),
("sales_category","المبيعات حسب التصنيف"),("sales_user","المبيعات حسب المستخدم"),("sales_branch","المبيعات حسب الفرع"),
("sales_customer","المبيعات حسب العميل"),("sales_payment","المبيعات حسب طريقة الدفع"),("discounts","الخصومات"),
("sales_returns","المرتجعات"),("purchases","المشتريات اليومية"),("purchases_supplier","المشتريات حسب المورد"),
("purchases_product","المشتريات حسب الصنف"),("purchases_period","المشتريات حسب الفترة"),("purchases_unpaid","المشتريات غير المسددة"),
("supplier_balance","الموردون المستحقون"),("stock","رصيد المخزون"),("stock_value","قيمة المخزون"),
("low_stock","الأصناف منخفضة المخزون"),("stagnant","الأصناف الراكدة"),("stock_movement","حركة صنف"),
("stock_in","دخول المخزون"),("stock_out","خروج المخزون"),("stock_transfer","تحويلات المخزون"),("stocktake","الجرد"),
("stocktake_diff","فروقات الجرد"),("damaged","التالف"),("customer_sales","مبيعات العميل"),("customer_debt","ديون العملاء"),
("customer_collections","التحصيلات"),("customer_aging","أعمار الديون"),("journal","دفتر اليومية"),("ledger","دفتر الأستاذ"),
("trial","ميزان المراجعة"),("income","قائمة الدخل"),("balance","الميزانية"),("cashflow","التدفق النقدي"),
("cash","حركة الصناديق"),("bank","حركة البنوك"),("expenses","المصروفات"),("tax","الضرائب")
]

class ReportsWindow(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent); self.setStyleSheet(APP_STYLE); self.setWindowTitle("مركز التقارير"); self.setMinimumSize(1320,800); self.setLayoutDirection(Qt.RightToLeft)
        root=QVBoxLayout(self); head=QHBoxLayout(); t=QLabel("مركز التقارير"); t.setObjectName("SectionTitle"); head.addWidget(t); head.addStretch()
        self.report=QComboBox()
        for key,name in REPORTS:self.report.addItem(name,key)
        self.report.currentIndexChanged.connect(self.load); head.addWidget(self.report)
        self.frm=QDateEdit(); self.frm.setCalendarPopup(True); self.frm.setDate(date.today()-timedelta(days=29))
        self.to=QDateEdit(); self.to.setCalendarPopup(True); self.to.setDate(date.today()); head.addWidget(QLabel("من:")); head.addWidget(self.frm); head.addWidget(QLabel("إلى:")); head.addWidget(self.to); root.addLayout(head)
        filters=QHBoxLayout(); self.filters={}
        for key,label in [("branch","الفرع"),("warehouse","المستودع"),("customer","العميل"),("supplier","المورد"),("product","الصنف"),("category","التصنيف"),("status","الحالة")]:
            w=QLineEdit(); w.setPlaceholderText(label); w.setMinimumWidth(105); w.textChanged.connect(self.load); self.filters[key]=w; filters.addWidget(w)
        root.addLayout(filters)
        actions=QHBoxLayout()
        for label,fn,obj in [("عرض التقرير",self.load,"Primary"),("Excel",self.export_excel,"Success"),("PDF",self.export_pdf,"Warning")]:
            b=QPushButton(label); b.setObjectName(obj); b.clicked.connect(fn); actions.addWidget(b)
        actions.addStretch(); root.addLayout(actions)
        self.table=QTableWidget(0,1); self.table.setAlternatingRowColors(True); self.table.setSelectionBehavior(QAbstractItemView.SelectRows); self.table.setEditTriggers(QAbstractItemView.NoEditTriggers); self.table.setSortingEnabled(True); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents); self.table.horizontalHeader().setStretchLastSection(True); root.addWidget(self.table,1)
        self.status=QLabel("جاهز"); root.addWidget(self.status); self.load()

    def _params(self):
        p={"f":self.frm.date().toString("yyyy-MM-dd"),"t":self.to.date().toString("yyyy-MM-dd")}
        for k,w in self.filters.items():p[k]=w.text().strip()
        return p

    def _run(self,s,sql,p): return s.execute(text(sql),p).all()

    def load(self,*_):
        p=self._params(); k=self.report.currentData()
        try:
            with get_session() as s: headers,rows=self._query(s,k,p)
            self.headers=headers; self.rows=[tuple(x) for x in rows]; self.table.setSortingEnabled(False); self.table.setColumnCount(len(headers)); self.table.setHorizontalHeaderLabels(headers); self.table.setRowCount(0)
            for vals in self.rows:
                r=self.table.rowCount(); self.table.insertRow(r)
                for c,v in enumerate(vals): self.table.setItem(r,c,QTableWidgetItem("" if v is None else str(v)))
            self.table.setSortingEnabled(True); self.status.setText(f"{self.report.currentText()} — {len(self.rows):,} سجل")
        except Exception as e:
            self.headers=["الحالة"]; self.rows=[("تعذر إنشاء التقرير: "+str(e),)]; self.table.setColumnCount(1); self.table.setHorizontalHeaderLabels(self.headers); self.table.setRowCount(1); self.table.setItem(0,0,QTableWidgetItem(self.rows[0][0])); self.status.setText("حدث خطأ في التقرير")

    def _query(self,s,k,p):
        ds="date(s.created_at) BETWEEN :f AND :t"; dp="date(pi.invoice_date) BETWEEN :f AND :t"
        if k in {"sales_day","sales_period","sales_payment"}:
            extra=" AND (:customer='' OR s.customer_id=CAST(:customer AS INTEGER)) AND (:branch='' OR s.branch_id=CAST(:branch AS INTEGER))"
            if k=="sales_day":p["f"]=p["t"]=date.today().isoformat()
            if k=="sales_payment":
                return ["طريقة الدفع","الفواتير","المبيعات"],self._run(s,"SELECT COALESCE(sp.payment_method,'غير محدد'),COUNT(DISTINCT s.id),COALESCE(SUM(sp.amount),0) FROM sales s LEFT JOIN sale_payments sp ON sp.sale_id=s.id WHERE "+ds+" AND s.status IN ('POSTED','completed')"+extra+" GROUP BY sp.payment_method ORDER BY 3 DESC",p)
            return ["الفواتير","قبل الضريبة","الخصم","الضريبة","الإجمالي","المدفوع","المتبقي"],self._run(s,"SELECT COUNT(*),SUM(subtotal),SUM(discount_amount),SUM(tax_amount),SUM(total_amount),SUM(paid_amount),SUM(due_amount) FROM sales s WHERE "+ds+" AND s.status IN ('POSTED','completed')"+extra,p)
        if k in {"sales_product","sales_category","sales_user","sales_branch","sales_customer","discounts"}:
            extra=""
            if k=="sales_product": head=["الصنف","الكمية","المبيعات","الخصم"]; sel="p.name_ar,SUM(si.quantity),SUM(si.line_total),SUM(si.discount_amount)"; grp="p.id,p.name_ar"; extra=" AND (:product='' OR p.id=CAST(:product AS INTEGER)) AND (:category='' OR p.category_id=CAST(:category AS INTEGER))"; joins="JOIN sale_items si ON si.sale_id=s.id JOIN products p ON p.id=si.product_id"
            elif k=="sales_category": head=["التصنيف","الكمية","المبيعات"]; sel="COALESCE(pc.name,'بدون تصنيف'),SUM(si.quantity),SUM(si.line_total)"; grp="pc.id,pc.name"; joins="JOIN sale_items si ON si.sale_id=s.id JOIN products p ON p.id=si.product_id LEFT JOIN product_categories pc ON pc.id=p.category_id"
            elif k=="sales_user": head=["المستخدم","الفواتير","المبيعات"]; sel="COALESCE(u.username,'غير محدد'),COUNT(DISTINCT s.id),SUM(s.total_amount)"; grp="u.id,u.username"; joins="LEFT JOIN users u ON u.id=s.cashier_id"
            elif k=="sales_branch": head=["الفرع","الفواتير","المبيعات"]; sel="b.name,COUNT(s.id),SUM(s.total_amount)"; grp="b.id,b.name"; joins="JOIN branches b ON b.id=s.branch_id"
            elif k=="sales_customer": head=["العميل","الفواتير","المبيعات","المدفوع","المتبقي"]; sel="COALESCE(c.name,'نقدي'),COUNT(s.id),SUM(s.total_amount),SUM(s.paid_amount),SUM(s.due_amount)"; grp="c.id,c.name"; joins="LEFT JOIN customers c ON c.id=s.customer_id"
            else: head=["الصنف","الخصم"]; sel="p.name_ar,SUM(si.discount_amount)"; grp="p.id,p.name_ar"; joins="JOIN sale_items si ON si.sale_id=s.id JOIN products p ON p.id=si.product_id"
            return head,self._run(s,f"SELECT {sel} FROM sales s {joins} WHERE {ds} AND s.status IN ('POSTED','completed'){extra} GROUP BY {grp} ORDER BY 1",p)
        if k=="sales_returns":return ["التاريخ","رقم المرتجع","البيع","المبلغ","الحالة"],self._run(s,"SELECT created_at,return_number,sale_id,total_amount,status FROM sale_returns WHERE date(created_at) BETWEEN :f AND :t ORDER BY id DESC",p)
        if k in {"purchases","purchases_period","purchases_unpaid"}:
            extra=" AND (:supplier='' OR pi.supplier_id=CAST(:supplier AS INTEGER))"
            if k=="purchases_unpaid":extra+=" AND COALESCE(pi.due_amount,0)>0"
            return ["الفواتير","قبل الضريبة","الضريبة","الإجمالي","المدفوع","المتبقي"],self._run(s,"SELECT COUNT(*),SUM(pi.subtotal),SUM(pi.tax_amount),SUM(pi.total_amount),SUM(pi.paid_amount),SUM(pi.due_amount) FROM purchase_invoices pi WHERE "+dp+extra,p)
        if k=="purchases_supplier":return ["المورد","الفواتير","المشتريات"],self._run(s,"SELECT COALESCE(sp.name,'غير محدد'),COUNT(pi.id),SUM(pi.total_amount) FROM purchase_invoices pi LEFT JOIN suppliers sp ON sp.id=pi.supplier_id WHERE "+dp+" GROUP BY sp.id,sp.name ORDER BY 3 DESC",p)
        if k=="purchases_product":return ["الصنف","الكمية","التكلفة"],self._run(s,"SELECT p.name_ar,SUM(pii.quantity),SUM(pii.quantity*pii.unit_cost) FROM purchase_invoice_items pii JOIN purchase_invoices pi ON pi.id=pii.purchase_invoice_id JOIN products p ON p.id=pii.product_id WHERE "+dp+" GROUP BY p.id,p.name_ar ORDER BY 3 DESC",p)
        if k=="supplier_balance":return ["المورد","رقم المورد","الرصيد","حد الائتمان"],self._run(s,"SELECT name,supplier_code,current_balance,credit_limit FROM suppliers ORDER BY name",p)
        if k=="stock":return ["الصنف","المستودع","الكمية","المتاح","متوسط التكلفة","القيمة"],self._run(s,"SELECT p.name_ar,w.name,sb.quantity,sb.quantity-sb.reserved_quantity,sb.average_cost,(sb.quantity-sb.reserved_quantity)*sb.average_cost FROM stock_balances sb JOIN products p ON p.id=sb.product_id JOIN warehouses w ON w.id=sb.warehouse_id WHERE (:product='' OR sb.product_id=CAST(:product AS INTEGER)) ORDER BY p.name_ar",p)
        if k=="stock_value":return ["قيمة المخزون"],self._run(s,"SELECT COALESCE(SUM((quantity-reserved_quantity)*average_cost),0) FROM stock_balances",p)
        if k=="low_stock":return ["الصنف","رمز الصنف","المتاح","الحد الأدنى"],self._run(s,"SELECT p.name_ar,p.sku,COALESCE(SUM(sb.quantity-sb.reserved_quantity),0),COALESCE(NULLIF(p.reorder_point,0),p.min_stock) FROM products p LEFT JOIN stock_balances sb ON sb.product_id=p.id WHERE p.is_active=1 GROUP BY p.id,p.name_ar,p.sku,p.reorder_point,p.min_stock HAVING COALESCE(SUM(sb.quantity-sb.reserved_quantity),0)<=COALESCE(NULLIF(p.reorder_point,0),p.min_stock) ORDER BY 3",p)
        if k=="stagnant":return ["الصنف","آخر حركة","أيام الركود","الكمية","القيمة"],self._run(s,"SELECT p.name_ar,sb.last_movement_at,CAST(julianday('now')-julianday(COALESCE(sb.last_movement_at,p.created_at)) AS INTEGER),SUM(sb.quantity-sb.reserved_quantity),SUM((sb.quantity-sb.reserved_quantity)*sb.average_cost) FROM products p JOIN stock_balances sb ON sb.product_id=p.id GROUP BY p.id,p.name_ar,sb.last_movement_at,p.created_at HAVING CAST(julianday('now')-julianday(COALESCE(sb.last_movement_at,p.created_at)) AS INTEGER)>=90 ORDER BY 3 DESC",p)
        if k in {"stock_movement","stock_in","stock_out","stock_transfer","damaged"}:
            typ={"stock_in":"IN","stock_out":"OUT","stock_transfer":"TRANSFER"}.get(k)
            extra=f" AND sm.movement_type=:typ" if typ else (" AND sm.movement_type IN ('DAMAGED','SCRAP')" if k=="damaged" else "")
            pp={**p,**({"typ":typ} if typ else {})}
            return ["التاريخ","الصنف","المستودع","الحركة","الكمية","التكلفة","المرجع"],self._run(s,"SELECT sm.created_at,p.name_ar,w.name,sm.movement_type,sm.quantity,sm.unit_cost,sm.reference_type FROM stock_movements sm JOIN products p ON p.id=sm.product_id JOIN warehouses w ON w.id=sm.warehouse_id WHERE date(sm.created_at) BETWEEN :f AND :t"+extra+" ORDER BY sm.id DESC",pp)
        if k=="stocktake":return ["الجرد","التاريخ","المستودع","الحالة"],self._run(s,"SELECT id,created_at,warehouse_id,status FROM stocktakes WHERE date(created_at) BETWEEN :f AND :t ORDER BY id DESC",p)
        if k=="stocktake_diff":return ["الجرد","الصنف","النظامي","الفعلي","الفرق"],self._run(s,"SELECT sti.stocktake_id,p.name_ar,sti.system_quantity,sti.counted_quantity,sti.counted_quantity-sti.system_quantity FROM stocktake_items sti JOIN products p ON p.id=sti.product_id ORDER BY sti.id DESC",p)
        if k=="purchase_returns":return ["التاريخ","رقم المرتجع","المورد","المبلغ","الحالة"],self._run(s,"SELECT created_at,return_number,supplier_id,total_amount,status FROM purchase_returns WHERE date(created_at) BETWEEN :f AND :t ORDER BY id DESC",p)
        if k=="customer_sales":return ["العميل","الفواتير","المبيعات"],self._run(s,"SELECT COALESCE(c.name,'نقدي'),COUNT(s.id),SUM(s.total_amount) FROM sales s LEFT JOIN customers c ON c.id=s.customer_id WHERE "+ds+" GROUP BY c.id,c.name ORDER BY 3 DESC",p)
        if k=="customer_debt":return ["العميل","الرصيد","حد الائتمان"],self._run(s,"SELECT name,current_balance,credit_limit FROM customers WHERE COALESCE(current_balance,0)>0 ORDER BY current_balance DESC",p)
        if k=="customer_collections":return ["التاريخ","العميل","المبلغ","الطريقة"],self._run(s,"SELECT payment_date,customer_id,amount,payment_method FROM customer_payments WHERE date(payment_date) BETWEEN :f AND :t ORDER BY id DESC",p)
        if k=="customer_aging":return ["العميل","الرصيد","أيام الاستحقاق"],self._run(s,"SELECT name,current_balance,0 FROM customers WHERE COALESCE(current_balance,0)>0 ORDER BY current_balance DESC",p)
        if k=="journal":return ["التاريخ","رقم القيد","البيان","الحالة"],self._run(s,"SELECT entry_date,entry_number,description,status FROM journal_entries WHERE date(entry_date) BETWEEN :f AND :t ORDER BY id DESC",p)
        if k in {"ledger","trial"}:
            h=["الحساب","رقم الحساب","مدين","دائن","الرصيد"] if k=="ledger" else ["الحساب","رقم الحساب","مدين","دائن"]
            sql="SELECT a.account_name,a.account_code,COALESCE(SUM(jl.debit),0),COALESCE(SUM(jl.credit),0)"+(",COALESCE(SUM(jl.debit-jl.credit),0)" if k=="ledger" else "")+" FROM journal_entry_lines jl JOIN journal_entries je ON je.id=jl.journal_entry_id JOIN accounts a ON a.id=jl.account_id WHERE je.status='POSTED' AND date(je.entry_date) BETWEEN :f AND :t GROUP BY a.id,a.account_name,a.account_code ORDER BY a.account_code"
            return h,self._run(s,sql,p)
        if k in {"income","balance"}:
            typ="REVENUE" if k=="income" else "ASSET"
            return ["الحساب","الرصيد"],self._run(s,"SELECT a.account_name,SUM(jl.credit-jl.debit) FROM journal_entry_lines jl JOIN journal_entries je ON je.id=jl.journal_entry_id JOIN accounts a ON a.id=jl.account_id WHERE je.status='POSTED' AND a.account_type=:typ AND date(je.entry_date) BETWEEN :f AND :t GROUP BY a.id,a.account_name ORDER BY a.account_code",{**p,"typ":typ})
        if k=="cashflow":return ["المصدر","القيمة"],self._run(s,"SELECT 'المبيعات النقدية',COALESCE(SUM(amount),0) FROM cash_transactions WHERE transaction_type='SALE' AND date(created_at) BETWEEN :f AND :t UNION ALL SELECT 'المصروفات',COALESCE(SUM(amount),0) FROM cash_transactions WHERE transaction_type IN ('EXPENSE','PAYMENT') AND date(created_at) BETWEEN :f AND :t",p)
        if k=="cash":return ["التاريخ","النوع","المبلغ","المرجع"],self._run(s,"SELECT created_at,transaction_type,amount,reference_type FROM cash_transactions WHERE date(created_at) BETWEEN :f AND :t ORDER BY id DESC",p)
        if k=="bank":return ["التاريخ","الحساب","النوع","المبلغ","المرجع"],self._run(s,"SELECT bt.transaction_date,ba.account_name,bt.transaction_type,bt.amount,bt.reference_type FROM bank_transactions bt JOIN bank_accounts ba ON ba.id=bt.bank_account_id WHERE date(bt.transaction_date) BETWEEN :f AND :t ORDER BY bt.id DESC",p)
        if k=="expenses":
            exists=s.execute(text("SELECT 1 FROM sqlite_master WHERE type='table' AND name='expenses'")).scalar()
            if not exists:return ["الحالة"],[("جدول المصروفات غير موجود في قاعدة البيانات الحالية",)]
            return ["التاريخ","الرقم","التصنيف","البيان","المبلغ","طريقة الدفع"],self._run(s,"SELECT expense_date,expense_number,category,description,amount,payment_method FROM expenses WHERE date(expense_date) BETWEEN :f AND :t ORDER BY id DESC",p)
        if k=="tax":return ["الفواتير","الضريبة"],self._run(s,"SELECT COUNT(*),COALESCE(SUM(tax_amount),0) FROM sales WHERE status IN ('POSTED','completed') AND date(created_at) BETWEEN :f AND :t",p)
        if k=="purchases_period":return ["الفواتير","الإجمالي"],self._run(s,"SELECT COUNT(*),COALESCE(SUM(total_amount),0) FROM purchase_invoices WHERE "+dp,p)
        return ["الحالة"],[("لا يوجد تعريف لهذا التقرير",)]

    def export_excel(self):
        try:
            path=ReportExportService.to_excel("تقرير_"+self.report.currentText(),self.headers,self.rows); QMessageBox.information(self,"التصدير",f"تم إنشاء ملف Excel:\\n{path}")
        except Exception as e: QMessageBox.critical(self,"فشل التصدير",str(e))

    def export_pdf(self):
        try:
            path=ReportExportService.to_pdf("تقرير_"+self.report.currentText(),self.headers,self.rows); QMessageBox.information(self,"التصدير",f"تم إنشاء ملف PDF:\\n{path}")
        except Exception as e: QMessageBox.critical(self,"فشل التصدير",str(e))
