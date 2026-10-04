from __future__ import annotations
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,QPushButton,QFrame,QTableWidget,QTableWidgetItem,QAbstractItemView,QScrollArea
from sqlalchemy import text
from app.database.connection import get_session
from app.ui.theme import APP_STYLE


def exists(s,t): return bool(s.execute(text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:t"),{'t':t}).scalar())

def cols(s,t): return [r[1] for r in s.connection().exec_driver_sql(f'PRAGMA table_info("{t}")').fetchall()]


def dashboard_panel(parent=None):
    w=QWidget(parent);w.setLayoutDirection(Qt.RightToLeft);w.setStyleSheet(APP_STYLE);root=QVBoxLayout(w);root.setContentsMargins(22,18,22,18);root.setSpacing(14)
    head=QHBoxLayout();title=QLabel('لوحة التحكم');title.setObjectName('PageTitle');head.addWidget(title);head.addStretch();stamp=QLabel('مؤشرات تشغيلية مباشرة من قاعدة البيانات');stamp.setObjectName('Muted');head.addWidget(stamp);root.addLayout(head)
    grid=QGridLayout();grid.setSpacing(12);root.addLayout(grid);cards=[('مبيعات اليوم','sales'),('مشتريات اليوم','purchases'),('صافي اليوم','net'),('عدد العملاء','customers'),('عدد الأصناف','products'),('منخفض المخزون','low'),('فواتير اليوم','invoices'),('مبالغ مستحقة','due')];nums={}
    for i,(title,key) in enumerate(cards):
        f=QFrame();f.setObjectName('DashboardCard');v=QVBoxLayout(f);v.setContentsMargins(18,16,18,16);a=QLabel(title);a.setObjectName('Muted');v.addWidget(a);n=QLabel('—');n.setObjectName('DashboardNumber');v.addWidget(n);nums[key]=n;grid.addWidget(f,i//4,i%4)
    body=QHBoxLayout();root.addLayout(body,1)
    alert_frame=QFrame();av=QVBoxLayout(alert_frame);av.addWidget(QLabel('التنبيهات التي تستحق الانتباه الآن'));alerts=QTableWidget(0,3);alerts.setHorizontalHeaderLabels(['التنبيه','العدد','الحالة']);alerts.setSelectionBehavior(QAbstractItemView.SelectRows);av.addWidget(alerts);body.addWidget(alert_frame,1)
    best_frame=QFrame();bv=QVBoxLayout(best_frame);bv.addWidget(QLabel('أفضل الأصناف مبيعًا'));best=QTableWidget(0,3);best.setHorizontalHeaderLabels(['الصنف','الكمية','قيمة المبيعات']);best.setSelectionBehavior(QAbstractItemView.SelectRows);bv.addWidget(best);body.addWidget(best_frame,1)
    def load():
        try:
            with get_session() as s:
                today="date('now','localtime')";sales=float(s.execute(text(f"SELECT COALESCE(SUM(total_amount),0) FROM sales WHERE date(created_at)={today} AND COALESCE(status,'') NOT IN ('CANCELLED','ملغي')")).scalar() or 0) if exists(s,'sales') else 0
                purchases=float(s.execute(text(f"SELECT COALESCE(SUM(total_amount),0) FROM purchase_invoices WHERE date(created_at)={today}")).scalar() or 0) if exists(s,'purchase_invoices') else 0
                customers=int(s.execute(text('SELECT COUNT(*) FROM customers')).scalar() or 0) if exists(s,'customers') else 0;products=int(s.execute(text('SELECT COUNT(*) FROM products')).scalar() or 0) if exists(s,'products') else 0
                invoices=int(s.execute(text(f"SELECT COUNT(*) FROM sales WHERE date(created_at)={today}")).scalar() or 0) if exists(s,'sales') else 0
                due=float(s.execute(text('SELECT COALESCE(SUM(due_amount),0) FROM sales WHERE due_amount>0')).scalar() or 0) if exists(s,'sales') and 'due_amount' in cols(s,'sales') else 0
                low=0
                if exists(s,'products'):
                    pc=cols(s,'products')
                    if 'min_stock' in pc and 'quantity' in pc:low=int(s.execute(text('SELECT COUNT(*) FROM products WHERE COALESCE(min_stock,0)>0 AND COALESCE(quantity,0)<=COALESCE(min_stock,0)')).scalar() or 0)
                nums['sales'].setText(f'{sales:,.2f}');nums['purchases'].setText(f'{purchases:,.2f}');nums['net'].setText(f'{sales-purchases:,.2f}');nums['customers'].setText(f'{customers:,}');nums['products'].setText(f'{products:,}');nums['low'].setText(f'{low:,}');nums['invoices'].setText(f'{invoices:,}');nums['due'].setText(f'{due:,.2f}')
                alerts.setRowCount(0)
                alert_rows=[('مخزون منخفض',low,'يحتاج مراجعة'),('فواتير آجلة',int(due>0),'توجد أرصدة مستحقة')]
                if exists(s,'notifications'):
                    n=int(s.execute(text("SELECT COUNT(*) FROM notifications WHERE COALESCE(is_read,0)=0")).scalar() or 0);alert_rows.append(('تنبيهات غير مقروءة',n,'راجع التنبيهات'))
                for x in alert_rows:
                    r=alerts.rowCount();alerts.insertRow(r)
                    for c,v in enumerate(x):alerts.setItem(r,c,QTableWidgetItem(str(v)))
                best.setRowCount(0)
                if exists(s,'sale_items') and exists(s,'products'):
                    pc=cols(s,'products');pn=next((x for x in ('name_ar','name','name_en','sku') if x in pc),'id')
                    rows=s.execute(text(f'SELECT COALESCE(p."{pn}",si.product_id),SUM(si.quantity),SUM(COALESCE(si.line_total,0)) FROM sale_items si LEFT JOIN products p ON p.id=si.product_id GROUP BY si.product_id ORDER BY SUM(si.quantity) DESC LIMIT 10')).all()
                    for x in rows:
                        r=best.rowCount();best.insertRow(r)
                        for c,v in enumerate(x):best.setItem(r,c,QTableWidgetItem(str(v)))
        except Exception as exc:
            stamp.setText('تعذر تحديث بعض المؤشرات')
    load();QTimer.singleShot(1500,load);w.refresh_dashboard=load;return w


def modern_build_ui(self):
    self.setStyleSheet(APP_STYLE);self.setMinimumSize(1360,820);self.setLayoutDirection(Qt.RightToLeft)
    root=QWidget();main=QVBoxLayout(root);main.setContentsMargins(0,0,0,0);main.setSpacing(0)
    top=QFrame();top.setObjectName('TopBar');tl=QHBoxLayout(top);tl.setContentsMargins(20,12,20,12);brand=QLabel('نظام القرطاسية');brand.setObjectName('TopTitle');tl.addWidget(brand);badge=QLabel('  ● يعمل محليًا  ');badge.setObjectName('Badge');tl.addWidget(badge);tl.addStretch();self.user_meta=QLabel('المستخدم: —');self.branch_meta=QLabel('الفرع: —');self.datetime_meta=QLabel('');
    for x in (self.user_meta,self.branch_meta,self.datetime_meta):x.setObjectName('TopMeta');tl.addWidget(x)
    main.addWidget(top)
    body=QHBoxLayout();body.setContentsMargins(10,10,10,10);body.setSpacing(10)
    side=QFrame();side.setObjectName('SideBar');side.setFixedWidth(260);sv=QVBoxLayout(side);sv.setContentsMargins(10,10,10,10);search=QPushButton('⌕  البحث العام');search.setObjectName('SideButton');search.clicked.connect(self.open_universal_search);sv.addWidget(search);pos=QPushButton('▣  نقطة البيع');pos.setObjectName('SideButton');pos.clicked.connect(self.open_pos);sv.addWidget(pos)
    groups=[('التشغيل',[('لوحة التحكم',self.show_dashboard),('المبيعات والفواتير',self.open_sales),('مرتجعات المبيعات',self.open_sales_returns)]),('المشتريات',[('المشتريات',self.open_purchases),('دورة المشتريات',self.open_purchase_workflow),('مرتجعات المشتريات',self.open_purchase_returns)]),('المخزون والأطراف',[('المنتجات',self.open_inventory),('التصنيفات',lambda:self.open_data('product_categories','التصنيفات')),('الوحدات',lambda:self.open_data('units','الوحدات')),('المستودعات',lambda:self.open_data('warehouses','المستودعات')),('حركات المخزون',lambda:self.open_data('stock_movements','حركات المخزون',editable=False)),('العملاء',self.open_parties),('الموردون',self.open_parties)]),('المالية',[('الخزينة',self.open_treasury),('البنوك والحسابات',self.open_treasury_accounts),('المحاسبة العامة',self.open_accounting),('دليل الحسابات',lambda:self.open_data('accounts','دليل الحسابات')),('الصناديق',lambda:self.open_data('cash_registers','الصناديق')),('الضرائب',lambda:self.open_data('tax_rates','الضرائب')),('الفواتير الضريبية',lambda:self.open_data('tax_invoices','الفواتير الضريبية',editable=False))]),('الإدارة',[('الشركات',lambda:self.open_data('companies','الشركات')),('الفروع',lambda:self.open_data('branches','الفروع')),('الموظفون',self.open_employees),('الرواتب',lambda:self.open_data('payroll_runs','مسيرات الرواتب')),('المستخدمون',lambda:self.open_data('users','المستخدمون')),('الأدوار والصلاحيات',self.open_permissions),('سجل التدقيق',lambda:self.open_data('audit_logs','سجل التدقيق',editable=False)),('التنبيهات',self.open_smart_operations)]),('النظام',[('الإعدادات',self.open_settings),('المستندات',lambda:self.open_data('documents','المستندات')),('النسخ الاحتياطي',self.open_backup)])]
    scroll=QScrollArea();scroll.setWidgetResizable(True);inner=QWidget();iv=QVBoxLayout(inner)
    for group,items in groups:
        gl=QLabel(group);gl.setObjectName('SideGroup');iv.addWidget(gl)
        for txt,fn in items:
            b=QPushButton(txt);b.setObjectName('SideButton');b.clicked.connect(fn);iv.addWidget(b)
    iv.addStretch();scroll.setWidget(inner);sv.addWidget(scroll,1);body.addWidget(side)
    self._modern_content=QWidget();self._modern_layout=QVBoxLayout(self._modern_content);self._modern_layout.setContentsMargins(0,0,0,0);body.addWidget(self._modern_content,1);main.addLayout(body,1);self.setCentralWidget(root)
    self._modern_show_dashboard()
    self._modern_clock=QTimer(self);self._modern_clock.timeout.connect(lambda:self.datetime_meta.setText(QTimer().tr('الآن')));self._modern_clock.start(1000)
    if getattr(self,'current_user',None):self._apply_modern_user()


def _apply_modern_user(self):
    u=getattr(self,'current_user',{}) or {};self.user_meta.setText('المستخدم: '+str(u.get('name_ar') or u.get('name') or u.get('username') or '—'));self.branch_meta.setText('الفرع: '+str(u.get('branch_name') or '—'))


def _modern_show_dashboard(self):
    while self._modern_layout.count():
        item=self._modern_layout.takeAt(0);w=item.widget();w and w.deleteLater()
    panel=dashboard_panel(self._modern_content);self._modern_layout.addWidget(panel);self._modern_dashboard=panel


def install(MainWindow):
    MainWindow.build_ui=modern_build_ui
    MainWindow.show_dashboard=_modern_show_dashboard
    MainWindow._apply_modern_user=_apply_modern_user
