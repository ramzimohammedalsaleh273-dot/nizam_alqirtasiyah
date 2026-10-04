from __future__ import annotations
from decimal import Decimal
import json
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,QDialog,QVBoxLayout,QHBoxLayout,QFormLayout,QLineEdit,QPushButton,
    QLabel,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QMessageBox,
    QDialogButtonBox,QDoubleSpinBox,QSpinBox,QCheckBox,QComboBox,QTextEdit,
    QTabWidget,QListWidget,QStackedWidget,QGroupBox,QListWidgetItem,QInputDialog
)
from sqlalchemy import text
from app.database.connection import get_session
from app.ui.theme import APP_STYLE
from app.ui.i18n import field_label,display_value
from app.services.pos_service import POSService
from app.services.pos_search_service import POSProductSearch
from app.services.pos_hold_service import POSHoldService
from app.services.party_service import PartyService
from app.services.tax_service import TaxService
from app.services.cashier_session_service import CashierSessionService
from app.services.sales_service import SalesService
from app.services.purchase_service import PurchaseService
from app.services.product_service import ProductService
from app.services.party_payment_service import PartyPaymentService
from app.services.treasury_operations_service import TreasuryOperationsService

TITLE_MAP={
'product_categories':'التصنيفات','units':'الوحدات','warehouses':'المستودعات','warehouse_zones':'مناطق التخزين','warehouse_aisles':'الممرات','warehouse_shelves':'الأرفف','warehouse_bins':'الخانات','stock_movements':'حركات المخزون','stocktakes':'الجرد','accounts':'دليل الحسابات','chart_of_accounts':'دليل الحسابات التفصيلي','cash_registers':'الصناديق','cash_transactions':'حركات الخزينة','cash_sessions':'الورديات','tax_rates':'الضرائب','tax_invoices':'الفواتير الضريبية','companies':'الشركات','branches':'الفروع','employees':'الموظفون','departments':'الأقسام','job_positions':'الوظائف','employee_attendance':'الحضور والانصراف','employee_leaves':'الإجازات','payroll_periods':'فترات الرواتب','payroll_runs':'مسيرات الرواتب','payroll_items':'تفاصيل الرواتب','users':'المستخدمون','login_sessions':'جلسات الدخول','roles':'الأدوار','permissions':'الصلاحيات','erp_roles':'الأدوار','erp_permissions':'الصلاحيات','erp_login_sessions':'جلسات الدخول','printing_services':'خدمات الطباعة','printing_orders':'طلبات الطباعة','approval_requests':'طلبات الاعتماد','audit_logs':'سجل التدقيق','audit_log':'سجل التدقيق','sync_queue':'المزامنة','sync_conflicts':'تعارضات المزامنة','sync_devices':'أجهزة المزامنة','fiscal_periods':'الفترات المالية','journal_entries':'القيود اليومية','journal_entry_lines':'تفاصيل القيود','notifications':'التنبيهات','documents':'المستندات','system_settings':'إعدادات النظام','document_sequences':'تسلسلات المستندات'}

FIELD_MAP={
'id':'الرقم','code':'الكود','name':'الاسم','name_ar':'الاسم بالعربية','name_en':'الاسم بالإنجليزية','sku':'رمز الصنف','barcode':'الباركود','phone':'الهاتف','mobile':'الجوال','email':'البريد الإلكتروني','address':'العنوان','tax_number':'الرقم الضريبي','commercial_number':'السجل التجاري','description':'الوصف','notes':'الملاحظات','status':'الحالة','is_active':'نشط','created_at':'تاريخ الإنشاء','updated_at':'آخر تحديث','company_id':'الشركة','branch_id':'الفرع','warehouse_id':'المستودع','category_id':'التصنيف','unit_id':'الوحدة','brand_id':'العلامة التجارية','parent_id':'الحساب الأب','supplier_id':'المورد','customer_id':'العميل','employee_id':'الموظف','user_id':'المستخدم','role_id':'الدور','quantity':'الكمية','reserved_quantity':'الكمية المحجوزة','available_quantity':'الكمية المتاحة','cost_price':'سعر التكلفة','sale_price':'سعر البيع','wholesale_price':'سعر الجملة','school_price':'سعر المدارس','corporate_price':'سعر الشركات','min_price':'أقل سعر','min_stock':'الحد الأدنى','max_stock':'الحد الأعلى','reorder_point':'نقطة إعادة الطلب','credit_limit':'حد الائتمان','current_balance':'الرصيد الحالي','opening_balance':'الرصيد الافتتاحي','account_code':'رقم الحساب','account_name':'اسم الحساب','account_type':'نوع الحساب','allow_posting':'يسمح بالترحيل','debit':'مدين','credit':'دائن','amount':'المبلغ','total_amount':'الإجمالي','subtotal':'الإجمالي قبل الضريبة','discount_amount':'الخصم','tax_amount':'الضريبة','paid_amount':'المدفوع','due_amount':'المتبقي','invoice_number':'رقم الفاتورة','invoice_date':'تاريخ الفاتورة','payment_method':'طريقة الدفع','reference_number':'رقم المرجع','transaction_type':'نوع الحركة','movement_type':'نوع الحركة','reference_type':'نوع المرجع','reference_id':'معرف المرجع','opened_at':'وقت الفتح','closed_at':'وقت الإغلاق','expected_balance':'الرصيد المتوقع','actual_balance':'الرصيد الفعلي','difference':'الفرق','setting_key':'اسم الإعداد','setting_value':'قيمة الإعداد','value_type':'نوع القيمة','document_no':'رقم المستند','document_type':'نوع المستند','entity_type':'نوع الكيان','entity_id':'معرف الكيان','title':'العنوان','message':'الرسالة','read_at':'تاريخ القراءة','is_read':'مقروء','payment_terms':'شروط السداد','currency_code':'العملة','supplier_code':'رقم المورد','customer_code':'رقم العميل','employee_no':'رقم الموظف','basic_salary':'الراتب الأساسي','salary':'الراتب','period_id':'الفترة','workflow_code':'رمز سير العمل','step_no':'رقم الخطوة','step_name':'اسم الخطوة','role_code':'رمز الدور'}

def ar_field(name):
    if name in FIELD_MAP:return FIELD_MAP[name]
    return field_label(name) if field_label(name)!='حقل غير معرّف' else 'حقل'

def exists(s,t):
    return bool(s.execute(text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:t"),{'t':t}).scalar())

def cols(s,t):
    return [r[1] for r in s.connection().exec_driver_sql(f'PRAGMA table_info("{t}")').fetchall()]

class RecordDialog(QDialog):
    def __init__(self,title,columns,record=None,parent=None):
        super().__init__(parent); self.setWindowTitle(title); self.setLayoutDirection(Qt.RightToLeft); self.setMinimumSize(700,520); self.setStyleSheet(APP_STYLE); self.widgets={}; record=record or {}; form=QFormLayout(self)
        for c in columns:
            n=c['name']; typ=str(c.get('type') or '').upper()
            if n in {'id','created_at','updated_at','last_login_at','read_at'}:continue
            if n in {'password_hash','token_hash','session_token','secret','private_key','xml_content'}:continue
            if 'BOOL' in typ or n in {'is_active','is_read','allow_posting','is_locked','is_group'}:w=QCheckBox(); w.setChecked(str(record.get(n,1)).lower() in {'1','true','yes','نعم'})
            elif any(x in typ for x in ('REAL','NUMERIC','DOUBLE','FLOAT','DECIMAL')):w=QDoubleSpinBox(); w.setRange(-999999999999,999999999999); w.setDecimals(2); w.setValue(float(record.get(n) or 0))
            elif 'INT' in typ:w=QSpinBox(); w.setRange(-2147483648,2147483647); w.setValue(int(record.get(n) or 0))
            elif n in {'description','notes','message','address'}:w=QTextEdit(str(record.get(n) or '')); w.setMinimumHeight(80)
            else:w=QLineEdit(str(record.get(n) or ''))
            self.widgets[n]=w; form.addRow(ar_field(n),w)
        b=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); b.accepted.connect(self.accept); b.rejected.connect(self.reject); form.addRow(b)
    def values(self):
        out={}
        for n,w in self.widgets.items():
            if isinstance(w,QCheckBox):out[n]=1 if w.isChecked() else 0
            elif isinstance(w,QTextEdit):out[n]=w.toPlainText().strip() or None
            elif isinstance(w,(QSpinBox,QDoubleSpinBox)):out[n]=w.value()
            else:out[n]=w.text().strip() or None
        return out

class AccessDataWindow(QWidget):
    """واجهة جداول عامة شبيهة بـ Access: بحث، فرز، فتح، جديد، تعديل، حذف، نسخ وتحديث."""
    def __init__(self,table_name,title=None,columns=None,editable=True,user=None,parent=None):
        super().__init__(parent); self.table_name=table_name; self.title_text=title or TITLE_MAP.get(table_name,ar_field(table_name)); self.requested=columns; self.editable=editable; self.user=user or {}; self.setWindowTitle(self.title_text); self.setMinimumSize(1180,720); self.setLayoutDirection(Qt.RightToLeft); self.setStyleSheet(APP_STYLE); self._build(); self._schema(); self.load()
    def _build(self):
        root=QVBoxLayout(self); h=QHBoxLayout(); t=QLabel(self.title_text); t.setObjectName('SectionTitle'); h.addWidget(t); h.addStretch(); root.addLayout(h)
        bar=QHBoxLayout(); bar.addWidget(QLabel('بحث شامل:')); self.search=QLineEdit(); self.search.setPlaceholderText('ابحث في جميع الحقول...'); self.search.textChanged.connect(lambda *_:self.load()); bar.addWidget(self.search,1); root.addLayout(bar)
        actions=QHBoxLayout()
        for cap,fn in [('جديد',self.add),('فتح',self.edit),('تعديل',self.edit),('حذف',self.delete),('تحديث',self.load)]:
            b=QPushButton(cap); b.clicked.connect(fn); actions.addWidget(b)
        actions.addStretch(); root.addLayout(actions)
        self.table=QTableWidget(); self.table.setSelectionBehavior(QAbstractItemView.SelectRows); self.table.setSelectionMode(QAbstractItemView.SingleSelection); self.table.setEditTriggers(QAbstractItemView.NoEditTriggers); self.table.setAlternatingRowColors(True); self.table.setSortingEnabled(True); self.table.doubleClicked.connect(lambda *_:self.edit()); root.addWidget(self.table,1)
        self.status=QLabel('جاهز'); root.addWidget(self.status)
    def _schema(self):
        with get_session() as s:
            if not exists(s,self.table_name):self.columns=[]; self.status.setText('الجدول غير موجود'); return
            names=cols(s,self.table_name)
        self.columns=[{'name':n} for n in names if n not in {'password_hash','token_hash','session_token','secret','private_key','xml_content'}]
        if self.requested:self.columns=[x for x in self.columns if x['name'] in set(self.requested)]
        self.table.setColumnCount(len(self.columns)); self.table.setHorizontalHeaderLabels([ar_field(x['name']) for x in self.columns]); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents); self.table.horizontalHeader().setStretchLastSection(True)
    def _id(self):
        r=self.table.currentRow();
        if r<0:return None
        for i,c in enumerate(self.columns):
            if c['name']=='id':
                try:return int(self.table.item(r,i).text())
                except:return None
        return None
    def load(self):
        if not self.columns:return
        q=self.search.text().strip(); names=[x['name'] for x in self.columns]; select=','.join(f'"{n}"' for n in names); params={}; where=''
        if q:
            searchable=[n for n in names if n not in {'id','created_at','updated_at'}]
            if searchable:
                where=' WHERE '+' OR '.join(f'CAST("{n}" AS TEXT) LIKE :q' for n in searchable); params['q']=f'%{q}%'
        try:
            with get_session() as s:rows=s.execute(text(f'SELECT {select} FROM "{self.table_name}"{where} ORDER BY rowid DESC LIMIT 500'),params).all()
            self.table.setSortingEnabled(False); self.table.setRowCount(0)
            for row in rows:
                r=self.table.rowCount(); self.table.insertRow(r)
                for c,v in enumerate(row):self.table.setItem(r,c,QTableWidgetItem(display_value(v)))
            self.table.setSortingEnabled(True); self.status.setText(f'عدد السجلات: {len(rows):,}')
        except Exception as e:QMessageBox.critical(self,'تعذر تحميل البيانات',str(e))
    def add(self):
        if not self.editable:return
        d=RecordDialog('جديد — '+self.title_text,self.columns,parent=self)
        if d.exec()!=QDialog.Accepted:return
        self._write(d.values(),None)
    def edit(self):
        if not self.editable:return
        rid=self._id()
        if rid is None:return QMessageBox.warning(self,'التعديل','حدد سجلًا أولًا.')
        with get_session() as s:rec=s.execute(text(f'SELECT * FROM "{self.table_name}" WHERE id=:id'),{'id':rid}).mappings().first()
        if not rec:return
        d=RecordDialog('تعديل — '+self.title_text,self.columns,dict(rec),self)
        if d.exec()!=QDialog.Accepted:return
        self._write(d.values(),rid)
    def _write(self,values,rid):
        allowed={x['name'] for x in self.columns}; values={k:v for k,v in values.items() if k in allowed and k not in {'id','created_at','updated_at'}}
        if not values:return
        try:
            with get_session() as s:
                if rid is None:
                    keys=list(values);s.execute(text(f'INSERT INTO "{self.table_name}" ({",".join(chr(34)+k+chr(34) for k in keys)}) VALUES ({",".join(":"+k for k in keys)})'),values)
                else:
                    sets=','.join(f'"{k}"=:{k}' for k in values);s.execute(text(f'UPDATE "{self.table_name}" SET {sets} WHERE id=:__id'),{**values,'__id':rid})
                s.commit()
            self.load()
        except Exception as e:QMessageBox.critical(self,'فشل الحفظ',str(e))
    def delete(self):
        if not self.editable:return
        rid=self._id()
        if rid is None:return QMessageBox.warning(self,'الحذف','حدد سجلًا أولًا.')
        if QMessageBox.question(self,'تأكيد الحذف','هل تريد حذف السجل المحدد؟')!=QMessageBox.Yes:return
        try:
            with get_session() as s:s.execute(text(f'DELETE FROM "{self.table_name}" WHERE id=:id'),{'id':rid});s.commit()
            self.load()
        except Exception as e:QMessageBox.critical(self,'فشل الحذف',str(e))

class PaymentDialog(QDialog):
    def __init__(self,total,customer_id=None,parent=None):
        super().__init__(parent);self.setWindowTitle('إتمام البيع');self.setLayoutDirection(Qt.RightToLeft);f=QFormLayout(self);self.total=Decimal(str(total));self.cash=QDoubleSpinBox();self.card=QDoubleSpinBox();self.transfer=QDoubleSpinBox();self.credit=QDoubleSpinBox()
        for w in (self.cash,self.card,self.transfer,self.credit):w.setRange(0,999999999);w.setDecimals(2)
        self.customer=QComboBox();self.customer.addItem('بدون عميل',None)
        try:
            for r in PartyService.customers():
                if r.get('is_active',1):self.customer.addItem(f"{r['id']} - {r['name']}",r['id'])
        except:pass
        for label,w in [('الإجمالي',QLabel(f'{self.total:.2f}')),('نقدًا',self.cash),('بطاقة',self.card),('تحويل بنكي',self.transfer),('آجل',self.credit),('العميل',self.customer)]:f.addRow(label,w)
        b=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);b.accepted.connect(self._ok);b.rejected.connect(self.reject);f.addRow(b)
        if customer_id is not None:
            i=self.customer.findData(customer_id)
            if i>=0:self.customer.setCurrentIndex(i)
    def _ok(self):
        total=sum(w.value() for w in (self.cash,self.card,self.transfer,self.credit));
        if round(total,2)!=round(float(self.total),2):QMessageBox.warning(self,'الدفع','مجموع الدفعات يجب أن يساوي الإجمالي.');return
        if self.credit.value()>0 and self.customer.currentData() is None:QMessageBox.warning(self,'الدفع','اختر العميل عند وجود بيع آجل.');return
        self.accept()
    def payments(self):
        return [{'method':m,'amount':w.value(),'reference_number':None} for m,w in [('cash',self.cash),('card',self.card),('bank_transfer',self.transfer),('credit',self.credit)] if w.value()>0]

class POSWindow(QWidget):
    def __init__(self,user=None,parent=None):
        super().__init__(parent);self.user=dict(user or {});self.cart=[];self.search_engine=POSProductSearch();self.setWindowTitle('نقطة البيع');self.setMinimumSize(1250,780);self.setLayoutDirection(Qt.RightToLeft);self.setStyleSheet(APP_STYLE);root=QVBoxLayout(self)
        top=QHBoxLayout();top.addWidget(QLabel('نقطة البيع'));top.addStretch();self.session=QLabel('الوردية: غير مفتوحة');top.addWidget(self.session);op=QPushButton('فتح الوردية');cl=QPushButton('إغلاق الوردية');op.clicked.connect(self.open_session);cl.clicked.connect(self.close_session);top.addWidget(op);top.addWidget(cl);root.addLayout(top)
        sr=QHBoxLayout();sr.addWidget(QLabel('بحث:'));self.search=QLineEdit();self.search.setPlaceholderText('باركود / رمز الصنف / الاسم');self.search.textChanged.connect(self.search_products);sr.addWidget(self.search,1);root.addLayout(sr)
        self.suggest=QTableWidget(0,5);self.suggest.setHorizontalHeaderLabels(['الكود','الصنف','الباركود','السعر','المتاح']);self.suggest.setSelectionBehavior(QAbstractItemView.SelectRows);self.suggest.doubleClicked.connect(lambda *_:self.add_suggestion());root.addWidget(self.suggest)
        self.table=QTableWidget(0,9);self.table.setHorizontalHeaderLabels(['م','الباركود/الكود','الصنف','الوحدة','الكمية','السعر','الخصم','الضريبة','الإجمالي']);self.table.setSelectionBehavior(QAbstractItemView.SelectRows);self.table.setAlternatingRowColors(True);self.table.itemChanged.connect(self.changed);root.addWidget(self.table,1)
        actions=QHBoxLayout();
        for cap,fn in [('حذف الصنف المحدد',self.remove),('تعديل الخصم',self.discount),('تعليق',self.hold),('استرجاع',self.resume),('تفريغ',self.clear),('إتمام البيع',self.complete)]:b=QPushButton(cap);b.clicked.connect(fn);actions.addWidget(b)
        root.addLayout(actions);self.total_label=QLabel('الإجمالي النهائي: 0.00');self.total_label.setStyleSheet('font-size:22px;font-weight:700');root.addWidget(self.total_label);self.refresh_session()
    def refresh_session(self):
        uid=self.user.get('id');sid=CashierSessionService.active_for(int(uid)) if uid else None;self.session.setText(f'الوردية: مفتوحة ({sid})' if sid else 'الوردية: غير مفتوحة');return sid
    def open_session(self):
        uid=self.user.get('id');amount,ok=QInputDialog.getDouble(self,'فتح الوردية','الرصيد الافتتاحي:',0,0,999999999,2)
        if not ok:return
        try:sid=CashierSessionService.open(int(uid) if uid else None,amount,opened_by=int(uid) if uid else None);QMessageBox.information(self,'تم',f'تم فتح الوردية رقم {sid}.');self.refresh_session()
        except PermissionError:
            try:
                with get_session() as s:
                    s.execute(text("INSERT INTO cashier_sessions(cashier_id,opening_amount,status,opened_by) VALUES(:c,:a,'OPEN',:u)"),{'c':uid,'a':amount,'u':uid});s.commit()
                self.refresh_session();QMessageBox.information(self,'تم','تم فتح الوردية.')
            except Exception as e:QMessageBox.critical(self,'فشل فتح الوردية',str(e))
        except Exception as e:QMessageBox.critical(self,'فشل فتح الوردية',str(e))
    def close_session(self):
        sid=self.refresh_session();
        if not sid:return QMessageBox.information(self,'الوردية','لا توجد وردية مفتوحة.')
        amount,ok=QInputDialog.getDouble(self,'إغلاق الوردية','النقد الفعلي:',0,0,999999999,2)
        if not ok:return
        try:r=CashierSessionService.close(sid,amount,closed_by=self.user.get('id'));QMessageBox.information(self,'تم الإغلاق',f"المتوقع: {r['expected']:.2f}\nالفعلي: {r['actual']:.2f}\nالفرق: {r['difference']:.2f}");self.refresh_session()
        except PermissionError:
            try:
                expected=CashierSessionService.expected(sid)
                with get_session() as s:s.execute(text("UPDATE cashier_sessions SET closing_amount=:a,expected_amount=:e,difference=:d,status='CLOSED',closed_at=CURRENT_TIMESTAMP,closed_by=:u WHERE id=:id"),{'a':amount,'e':expected,'d':amount-expected,'u':self.user.get('id'),'id':sid});s.commit()
                QMessageBox.information(self,'تم الإغلاق',f'المتوقع: {expected:.2f}\nالفعلي: {amount:.2f}\nالفرق: {amount-expected:.2f}');self.refresh_session()
            except Exception as e:QMessageBox.critical(self,'فشل الإغلاق',str(e))
        except Exception as e:QMessageBox.critical(self,'فشل الإغلاق',str(e))
    def search_products(self,term):
        self.suggest.setRowCount(0);term=term.strip()
        if not term:return
        try:rows=self.search_engine.search(term)[:40]
        except:return
        for p in rows:
            r=self.suggest.rowCount();self.suggest.insertRow(r);vals=[p.get('sku') or '',p.get('name_ar') or p.get('name_en') or '',p.get('barcode') or '',f"{float(p.get('sale_price') or 0):.2f}",str(p.get('available_quantity',p.get('stock',0)) or 0)]
            for c,v in enumerate(vals):self.suggest.setItem(r,c,QTableWidgetItem(str(v)))
    def add_suggestion(self):
        r=self.suggest.currentRow();
        if r<0:return
        key=self.suggest.item(r,2).text() or self.suggest.item(r,0).text();ps=self.search_engine.search(key)
        if ps:self.add_product(ps[0])
    def add_product(self,p):
        pid=int(p['id']);found=next((x for x in self.cart if x['product_id']==pid),None)
        if found:found['quantity']+=1
        else:self.cart.append({'product_id':pid,'sku':p.get('sku') or '','name':p.get('name_ar') or p.get('name_en') or '','unit':p.get('unit_name') or p.get('unit') or '—','quantity':1,'unit_price':float(p.get('sale_price') or 0),'discount':0})
        self.refresh()
    def changed(self,item):
        if item.column()!=4:return
        try:self.cart[item.row()]['quantity']=max(0,float(item.text()));self.refresh()
        except: self.refresh()
    def refresh(self):
        self.table.blockSignals(True);self.table.setRowCount(len(self.cart));grand=Decimal('0')
        for r,x in enumerate(self.cart):
            gross=Decimal(str(x['quantity']))*Decimal(str(x['unit_price']));disc=Decimal(str(x['discount']));tax=TaxService.calculate(gross-disc);grand+=Decimal(str(tax['total']));vals=[r+1,x['sku'],x['name'],x['unit'],x['quantity'],f"{x['unit_price']:.2f}",f"{x['discount']:.2f}",f"{tax['tax']:.2f}",f"{tax['total']:.2f}"]
            for c,v in enumerate(vals):self.table.setItem(r,c,QTableWidgetItem(str(v)))
        self.table.blockSignals(False);self.total_label.setText(f'الإجمالي النهائي: {grand:.2f}')
    def current_total(self):return Decimal(self.total_label.text().split(':')[-1].strip())
    def remove(self):
        r=self.table.currentRow();
        if 0<=r<len(self.cart):self.cart.pop(r);self.refresh()
    def discount(self):
        r=self.table.currentRow();
        if r<0 or r>=len(self.cart):return
        x=self.cart[r];maxv=x['quantity']*x['unit_price'];v,ok=QInputDialog.getDouble(self,'تعديل الخصم','قيمة الخصم:',x['discount'],0,maxv,2)
        if ok:x['discount']=v;self.refresh()
    def clear(self):self.cart=[];self.refresh()
    def hold(self):
        if not self.cart:return
        try:r=POSHoldService.hold(self.cart,cashier_id=self.user.get('id'),warehouse_id=int(self.user.get('warehouse_id') or 1),branch_id=int(self.user.get('branch_id') or 1));QMessageBox.information(self,'تم التعليق',f"تم تعليق الفاتورة {r['hold_number']}");self.clear()
        except Exception as e:QMessageBox.critical(self,'فشل التعليق',str(e))
    def resume(self):
        try:
            rows=POSHoldService.list_held(self.user.get('id')); 
            if not rows:return QMessageBox.information(self,'استرجاع','لا توجد فواتير معلقة.')
            labels=[f"{r['id']} - {r['hold_number']}" for r in rows];chosen,ok=QInputDialog.getItem(self,'استرجاع','اختر الفاتورة:',labels,0,False)
            if not ok:return
            hid=int(chosen.split(' - ',1)[0]);r=POSHoldService.resume(hid,self.user.get('id'));self.cart=r['items'];self.refresh()
        except Exception as e:QMessageBox.critical(self,'فشل الاسترجاع',str(e))
    def complete(self):
        if not self.cart:return QMessageBox.warning(self,'إتمام البيع','الفاتورة فارغة.')
        d=PaymentDialog(self.current_total(),self.user.get('customer_id'),self)
        if d.exec()!=QDialog.Accepted:return
        try:
            payments=d.payments();r=POSService.create_sale(self.cart,payment_method=payments[0]['method'],payments=payments,customer_id=d.customer.currentData(),warehouse_id=int(self.user.get('warehouse_id') or 1),branch_id=int(self.user.get('branch_id') or 1),cashier_id=int(self.user.get('id') or 1));QMessageBox.information(self,'تم البيع',f"الفاتورة: {r['invoice_number']}\nالإجمالي: {r['total']:.2f}");self.clear()
        except Exception as e:QMessageBox.critical(self,'فشل البيع',str(e))

class DetailWindow(QWidget):
    def __init__(self,title,number,loader,parent=None):
        super().__init__(parent);self.setWindowTitle(title);self.setMinimumSize(1200,760);self.setLayoutDirection(Qt.RightToLeft);self.setStyleSheet(APP_STYLE);self.loader=loader;root=QVBoxLayout(self);h=QHBoxLayout();self.search=QLineEdit(str(number or ''));self.search.setPlaceholderText('رقم المستند');b=QPushButton('فتح');b.clicked.connect(self.load);h.addWidget(self.search,1);h.addWidget(b);root.addLayout(h);self.title=QLabel(title);self.title.setObjectName('SectionTitle');root.addWidget(self.title);self.tabs=QTabWidget();root.addWidget(self.tabs,1);self.load()
    def fill(self,caption,headers,rows):
        t=QTableWidget(0,len(headers));t.setHorizontalHeaderLabels(headers);t.setSelectionBehavior(QAbstractItemView.SelectRows);t.setEditTriggers(QAbstractItemView.NoEditTriggers);t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents);t.horizontalHeader().setStretchLastSection(True)
        for row in rows:
            r=t.rowCount();t.insertRow(r)
            for c,v in enumerate(row):t.setItem(r,c,QTableWidgetItem('' if v is None else str(v)))
        self.tabs.addTab(t,caption)
    def load(self):
        try:self.tabs.clear();data=self.loader(self.search.text().strip());
        except Exception as e:QMessageBox.critical(self,'فشل فتح الملف',str(e));return
        if not data:return QMessageBox.warning(self,'غير موجود','لم يتم العثور على المستند.')
        self.fill('البيانات',['الحقل','القيمة'],[(ar_field(k),v) for k,v in data.items() if not isinstance(v,(list,dict))]);
        for k,v in data.items():
            if isinstance(v,list) and v and isinstance(v[0],dict):self.fill(TITLE_MAP.get(k,k),[ar_field(x) for x in v[0].keys()],[list(x.values()) for x in v])

class SalesWindow(QWidget):
    def __init__(self,user=None,parent=None):
        super().__init__(parent);self.user=user or {};self.setWindowTitle('المبيعات والفواتير');self.setMinimumSize(1200,720);self.setLayoutDirection(Qt.RightToLeft);self.setStyleSheet(APP_STYLE);root=QVBoxLayout(self);h=QHBoxLayout();h.addWidget(QLabel('المبيعات والفواتير'));h.addStretch();self.search=QLineEdit();self.search.setPlaceholderText('بحث برقم الفاتورة');b=QPushButton('فتح الفاتورة');b.clicked.connect(self.open);h.addWidget(self.search);h.addWidget(b);r=QPushButton('تحديث');r.clicked.connect(self.load);h.addWidget(r);root.addLayout(h);self.table=QTableWidget(0,8);self.table.setHorizontalHeaderLabels(['رقم الفاتورة','التاريخ','العميل','المستخدم','الإجمالي','المدفوع','المتبقي','الحالة']);self.table.setSelectionBehavior(QAbstractItemView.SelectRows);self.table.doubleClicked.connect(lambda *_:self.open_selected());root.addWidget(self.table,1);self.load()
    def load(self):
        try:rows=SalesService.list_sales();q=self.search.text().strip().lower();
        except Exception as e:return QMessageBox.critical(self,'المبيعات',str(e))
        if q:rows=[r for r in rows if q in str(r.get('invoice_number') or '').lower()]
        self.table.setRowCount(0)
        for x in rows:
            r=self.table.rowCount();self.table.insertRow(r);vals=[x.get('invoice_number'),x.get('created_at'),x.get('customer_name') or 'عميل نقدي',x.get('cashier_name') or '—',x.get('total_amount'),x.get('paid_amount'),x.get('due_amount'),display_value(x.get('status'))]
            for c,v in enumerate(vals):self.table.setItem(r,c,QTableWidgetItem('' if v is None else str(v)))
    def open(self):
        n=self.search.text().strip();
        if not n:return self.open_selected()
        self._show(n)
    def open_selected(self):
        r=self.table.currentRow();
        if r<0:return QMessageBox.warning(self,'فتح الفاتورة','حدد فاتورة أولًا.')
        self._show(self.table.item(r,0).text())
    def _show(self,n):
        from app.services.sales_invoice_service import SalesInvoiceService
        try:data=SalesInvoiceService.find_by_number(n)
        except Exception as e:return QMessageBox.critical(self,'فشل فتح الفاتورة',str(e))
        if not data:return QMessageBox.warning(self,'غير موجود','لم يتم العثور على الفاتورة.')
        w=DetailWindow('ملف فاتورة البيع',n,lambda x:SalesInvoiceService.find_by_number(x),self);w.show();w.raise_();w.activateWindow();self._detail=w

class PurchasesWindow(QWidget):
    def __init__(self,user=None,parent=None):
        super().__init__(parent);self.user=user or {};self.setWindowTitle('المشتريات والفواتير');self.setMinimumSize(1250,740);self.setLayoutDirection(Qt.RightToLeft);self.setStyleSheet(APP_STYLE);root=QVBoxLayout(self);h=QHBoxLayout();h.addWidget(QLabel('المشتريات والفواتير'));h.addStretch();self.search=QLineEdit();self.search.setPlaceholderText('بحث برقم الفاتورة أو المورد');h.addWidget(self.search);new=QPushButton('جديد');new.clicked.connect(self.new_invoice);openb=QPushButton('فتح');openb.clicked.connect(self.open_selected);edit=QPushButton('تعديل');edit.clicked.connect(self.open_selected);delete=QPushButton('حذف');delete.clicked.connect(self.delete_selected);refresh=QPushButton('تحديث');refresh.clicked.connect(self.load)
        for b in (new,openb,edit,delete,refresh):h.addWidget(b)
        root.addLayout(h);self.table=QTableWidget(0,7);self.table.setHorizontalHeaderLabels(['رقم الفاتورة','التاريخ','المورد','الإجمالي','المدفوع','المتبقي','الحالة']);self.table.setSelectionBehavior(QAbstractItemView.SelectRows);self.table.doubleClicked.connect(lambda *_:self.open_selected());root.addWidget(self.table,1);self.load()
    def load(self):
        try:rows=PurchaseService.list_purchases()
        except Exception as e:return QMessageBox.critical(self,'المشتريات',str(e))
        q=self.search.text().strip().lower();rows=[x for x in rows if not q or q in str(x.get('invoice_number') or '').lower() or q in str(x.get('supplier_name') or '').lower()];self.table.setRowCount(0)
        for x in rows:
            r=self.table.rowCount();self.table.insertRow(r);vals=[x.get('invoice_number'),x.get('invoice_date'),x.get('supplier_name') or '—',x.get('total_amount'),x.get('paid_amount'),x.get('due_amount'),display_value(x.get('status'))]
            for c,v in enumerate(vals):self.table.setItem(r,c,QTableWidgetItem('' if v is None else str(v)))
    def selected_id(self):
        r=self.table.currentRow();return int(PurchaseService.list_purchases()[r]['id']) if r>=0 else None
    def open_selected(self):
        rid=self.selected_id();
        if rid is None:return QMessageBox.warning(self,'فتح','حدد فاتورة أولًا.')
        from app.ui.purchase_invoice_window import PurchaseInvoiceWindow
        w=PurchaseInvoiceWindow(self,rid);w.show();w.raise_();w.activateWindow();self._detail=w
    def new_invoice(self):QMessageBox.information(self,'فاتورة شراء','استخدم دورة المشتريات لإنشاء فاتورة مرتبطة بالمستندات والاستلام.')
    def delete_selected(self):
        rid=self.selected_id();
        if rid is None:return
        if QMessageBox.question(self,'حذف','حذف فاتورة الشراء المحددة؟')!=QMessageBox.Yes:return
        try:
            with get_session() as s:s.execute(text('DELETE FROM purchase_invoices WHERE id=:id'),{'id':rid});s.commit();self.load()
        except Exception as e:QMessageBox.critical(self,'فشل الحذف',str(e))

class ProductCardDialog(QDialog):
    def __init__(self,pid,parent=None):
        super().__init__(parent);self.pid=int(pid);self.setWindowTitle('بطاقة الصنف');self.setMinimumSize(1250,800);self.setLayoutDirection(Qt.RightToLeft);self.setStyleSheet(APP_STYLE);root=QVBoxLayout(self);self.title=QLabel();self.title.setObjectName('SectionTitle');root.addWidget(self.title);self.tabs=QTabWidget();root.addWidget(self.tabs,1);self.build()
    def table(self,caption,headers,rows):
        t=QTableWidget(0,len(headers));t.setHorizontalHeaderLabels(headers);t.setAlternatingRowColors(True);t.setSelectionBehavior(QAbstractItemView.SelectRows);t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents);t.horizontalHeader().setStretchLastSection(True)
        for row in rows:
            r=t.rowCount();t.insertRow(r)
            for c,v in enumerate(row):t.setItem(r,c,QTableWidgetItem('' if v is None else display_value(v)))
        self.tabs.addTab(t,caption)
    def build(self):
        with get_session() as s:p=s.execute(text('SELECT * FROM products WHERE id=:id'),{'id':self.pid}).mappings().first()
        if not p:return self.title.setText('الصنف غير موجود')
        self.title.setText('بطاقة الصنف: '+str(p.get('name_ar') or p.get('name_en') or '—'))
        self.table('البيانات',['الحقل','القيمة'],[(ar_field(k),v) for k,v in p.items() if k not in {'id','created_at','updated_at'}])
        self.table('الأسعار',['السعر','القيمة'],[(ar_field(k),p.get(k)) for k in ('cost_price','sale_price','wholesale_price','school_price','corporate_price','min_price') if k in p])
        with get_session() as s:
            bar=s.execute(text('SELECT barcode,is_primary FROM product_barcodes WHERE product_id=:id ORDER BY id'),{'id':self.pid}).mappings().all();stock=s.execute(text('SELECT w.name,sb.quantity,sb.reserved_quantity,sb.quantity-sb.reserved_quantity,sb.average_cost,sb.last_movement_at FROM stock_balances sb LEFT JOIN warehouses w ON w.id=sb.warehouse_id WHERE sb.product_id=:id'),{'id':self.pid}).all();moves=s.execute(text('SELECT created_at,movement_type,reference_type,reference_id,quantity,unit_cost FROM stock_movements WHERE product_id=:id ORDER BY id DESC LIMIT 500'),{'id':self.pid}).all();sales=s.execute(text('SELECT s.invoice_number,s.created_at,si.quantity,si.unit_price,si.line_total FROM sale_items si JOIN sales s ON s.id=si.sale_id WHERE si.product_id=:id ORDER BY s.id DESC LIMIT 500'),{'id':self.pid}).all();purchases=s.execute(text('SELECT pi.invoice_number,pi.invoice_date,pii.quantity,pii.unit_cost FROM purchase_invoice_items pii JOIN purchase_invoices pi ON pi.id=pii.purchase_invoice_id WHERE pii.product_id=:id ORDER BY pi.id DESC LIMIT 500'),{'id':self.pid}).all()
        self.table('الباركود',['الباركود','أساسي'],bar);self.table('المخزون',['المستودع','الكمية','المحجوز','المتاح','متوسط التكلفة','آخر حركة'],stock);self.table('حركات المخزون',['التاريخ','الحركة','المصدر','المرجع','الكمية','التكلفة'],moves);self.table('المبيعات',['الفاتورة','التاريخ','الكمية','السعر','الإجمالي'],sales);self.table('المشتريات',['الفاتورة','التاريخ','الكمية','التكلفة'],purchases);self.table('الملاحظات',['البيان','النص'],[('الوصف',p.get('description')),('الملاحظات',p.get('notes'))])

class InventoryWindow(QWidget):
    def __init__(self,user=None,parent=None):
        super().__init__(parent);self.user=user or {};self.setWindowTitle('المنتجات والمخزون');self.setMinimumSize(1250,720);self.setLayoutDirection(Qt.RightToLeft);self.setStyleSheet(APP_STYLE);root=QVBoxLayout(self);h=QHBoxLayout();h.addWidget(QLabel('المنتجات والمخزون'));h.addStretch();self.search=QLineEdit();self.search.setPlaceholderText('باركود / رمز الصنف / الاسم');self.search.textChanged.connect(lambda *_:self.load());h.addWidget(self.search)
        for cap,fn in [('جديد',self.add),('فتح بطاقة الصنف',self.open_card),('تعديل',self.edit),('حذف',self.delete),('تحديث',self.load)]:b=QPushButton(cap);b.clicked.connect(fn);h.addWidget(b)
        root.addLayout(h);self.table=QTableWidget(0,10);self.table.setHorizontalHeaderLabels(['الرقم','الباركود','رمز الصنف','اسم الصنف','التصنيف','الوحدة','التكلفة','سعر البيع','الكمية','الحالة']);self.table.setSelectionBehavior(QAbstractItemView.SelectRows);self.table.doubleClicked.connect(lambda *_:self.open_card());root.addWidget(self.table,1);self.load()
    def load(self):
        q=self.search.text().strip();
        try:
            with get_session() as s:
                rows=s.execute(text("""SELECT p.id,COALESCE(pb.barcode,p.barcode,''),p.sku,p.name_ar,c.name,u.name,p.cost_price,p.sale_price,COALESCE(SUM(sb.quantity-sb.reserved_quantity),0),p.is_active FROM products p LEFT JOIN product_barcodes pb ON pb.product_id=p.id AND pb.is_primary=1 LEFT JOIN product_categories c ON c.id=p.category_id LEFT JOIN units u ON u.id=p.unit_id LEFT JOIN stock_balances sb ON sb.product_id=p.id WHERE (:q='') OR p.sku LIKE :like OR p.name_ar LIKE :like OR COALESCE(pb.barcode,p.barcode,'') LIKE :like GROUP BY p.id ORDER BY p.id DESC LIMIT 1000"""),{'q':q,'like':f'%{q}%'}).all()
        except Exception as e:return QMessageBox.critical(self,'المخزون',str(e))
        self.table.setRowCount(0)
        for x in rows:
            r=self.table.rowCount();self.table.insertRow(r)
            for c,v in enumerate(x):self.table.setItem(r,c,QTableWidgetItem(display_value(v)))
    def pid(self):
        r=self.table.currentRow();return int(self.table.item(r,0).text()) if r>=0 else None
    def open_card(self):
        pid=self.pid();
        if pid is None:return QMessageBox.warning(self,'بطاقة الصنف','حدد صنفًا أولًا.')
        ProductCardDialog(pid,self).exec()
    def add(self):
        d=RecordDialog('إضافة صنف',[{'name':x} for x in ['sku','name_ar','barcode','cost_price','sale_price','min_stock','max_stock','description','notes']],parent=self)
        if d.exec()!=QDialog.Accepted:return
        v=d.values()
        try:
            ProductService.create_product(v.get('sku') or '',v.get('name_ar') or '',float(v.get('cost_price') or 0),float(v.get('sale_price') or 0),v.get('barcode'),0,1,user_id=self.user.get('id'));self.load()
        except Exception as e:QMessageBox.critical(self,'فشل إضافة الصنف',str(e))
    def edit(self):
        pid=self.pid();
        if pid is None:return QMessageBox.warning(self,'تعديل','حدد صنفًا أولًا.')
        with get_session() as s:r=s.execute(text('SELECT * FROM products WHERE id=:id'),{'id':pid}).mappings().first()
        d=RecordDialog('تعديل بطاقة الصنف',[{'name':x} for x in ['sku','name_ar','barcode','cost_price','sale_price','min_stock','max_stock','description','notes']],dict(r),self)
        if d.exec()!=QDialog.Accepted:return
        v=d.values()
        try:ProductService.update_product(pid,v.get('sku'),v.get('name_ar'),float(v.get('cost_price') or 0),float(v.get('sale_price') or 0),user_id=self.user.get('id'));self.load()
        except Exception as e:QMessageBox.critical(self,'فشل التعديل',str(e))
    def delete(self):
        pid=self.pid();
        if pid is None:return
        if QMessageBox.question(self,'حذف','هل تريد تعطيل الصنف؟')!=QMessageBox.Yes:return
        try:
            with get_session() as s:s.execute(text('UPDATE products SET is_active=0 WHERE id=:id'),{'id':pid});s.commit();self.load()
        except Exception as e:QMessageBox.critical(self,'فشل العملية',str(e))

class PartyCardDialog(QDialog):
    def __init__(self,pid,supplier=False,parent=None):
        super().__init__(parent);self.pid=int(pid);self.supplier=supplier;self.setWindowTitle('بطاقة المورد' if supplier else 'بطاقة العميل');self.setMinimumSize(1200,780);self.setLayoutDirection(Qt.RightToLeft);self.setStyleSheet(APP_STYLE);root=QVBoxLayout(self);self.title=QLabel();self.title.setObjectName('SectionTitle');root.addWidget(self.title);self.tabs=QTabWidget();root.addWidget(self.tabs);self.build()
    def addtab(self,title,headers,rows):
        t=QTableWidget(0,len(headers));t.setHorizontalHeaderLabels(headers);t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents);t.horizontalHeader().setStretchLastSection(True)
        for row in rows:
            r=t.rowCount();t.insertRow(r)
            for c,v in enumerate(row):t.setItem(r,c,QTableWidgetItem(display_value(v)))
        self.tabs.addTab(t,title)
    def build(self):
        table='suppliers' if self.supplier else 'customers'
        with get_session() as s:p=s.execute(text(f'SELECT * FROM {table} WHERE id=:id'),{'id':self.pid}).mappings().first()
        if not p:return self.title.setText('السجل غير موجود')
        self.title.setText(('بطاقة المورد: ' if self.supplier else 'بطاقة العميل: ')+str(p.get('name') or '—'));self.addtab('البيانات',['الحقل','القيمة'],[(ar_field(k),v) for k,v in p.items() if k not in {'id','created_at','updated_at'}])
        with get_session() as s:
            if self.supplier:
                inv=s.execute(text('SELECT invoice_number,invoice_date,total_amount,paid_amount,due_amount,status FROM purchase_invoices WHERE supplier_id=:id ORDER BY id DESC LIMIT 500'),{'id':self.pid}).all();ret=s.execute(text('SELECT return_number,total_amount,status,reason,created_at FROM purchase_returns WHERE supplier_id=:id ORDER BY id DESC LIMIT 500'),{'id':self.pid}).all();pay=s.execute(text('SELECT payment_number,payment_date,amount,payment_method,reference_number FROM supplier_payments WHERE supplier_id=:id ORDER BY id DESC LIMIT 500'),{'id':self.pid}).all();trans=s.execute(text('SELECT created_at,transaction_type,amount,reference_type,reference_id,balance_after FROM supplier_transactions WHERE supplier_id=:id ORDER BY id DESC LIMIT 500'),{'id':self.pid}).all()
            else:
                inv=s.execute(text('SELECT invoice_number,created_at,total_amount,paid_amount,due_amount,status FROM sales WHERE customer_id=:id ORDER BY id DESC LIMIT 500'),{'id':self.pid}).all();ret=s.execute(text('SELECT return_number,total_amount,status,reason,created_at FROM sale_returns WHERE customer_id=:id ORDER BY id DESC LIMIT 500'),{'id':self.pid}).all();pay=s.execute(text('SELECT payment_number,payment_date,amount,payment_method,reference_number FROM customer_payments WHERE customer_id=:id ORDER BY id DESC LIMIT 500'),{'id':self.pid}).all();trans=s.execute(text('SELECT created_at,transaction_type,amount,reference_type,reference_id,balance_after FROM customer_transactions WHERE customer_id=:id ORDER BY id DESC LIMIT 500'),{'id':self.pid}).all()
        self.addtab('الفواتير',['رقم الفاتورة','التاريخ','الإجمالي','المدفوع','المتبقي','الحالة'],inv);self.addtab('المرتجعات',['رقم المرتجع','المبلغ','الحالة','السبب','التاريخ'],ret);self.addtab('الدفعات',['رقم السند','التاريخ','المبلغ','طريقة الدفع','المرجع'],pay);self.addtab('كشف الحساب',['التاريخ','الحركة','المبلغ','نوع المرجع','المرجع','الرصيد بعد الحركة'],trans)

class PartiesWindow(QWidget):
    def __init__(self,user=None,parent=None):
        super().__init__(parent);self.user=user or {};self.setWindowTitle('العملاء والموردون');self.setMinimumSize(1200,720);self.setLayoutDirection(Qt.RightToLeft);self.setStyleSheet(APP_STYLE);root=QVBoxLayout(self);h=QHBoxLayout();h.addWidget(QLabel('العملاء والموردون'));h.addStretch();self.search=QLineEdit();self.search.setPlaceholderText('بحث بالاسم أو الكود أو الهاتف');self.search.textChanged.connect(self.load);h.addWidget(self.search);root.addLayout(h);a=QHBoxLayout();
        for cap,fn in [('جديد عميل',lambda:self.add(False)),('جديد مورد',lambda:self.add(True)),('فتح البطاقة',self.open_card),('تحديث',self.load)]:b=QPushButton(cap);b.clicked.connect(fn);a.addWidget(b)
        root.addLayout(a);self.tabs=QTabWidget();self.customers=self.table();self.suppliers=self.table();self.tabs.addTab(self.customers,'العملاء');self.tabs.addTab(self.suppliers,'الموردون');root.addWidget(self.tabs,1);self.customers.doubleClicked.connect(lambda *_:self.open_card());self.suppliers.doubleClicked.connect(lambda *_:self.open_card());self.load()
    def table(self):t=QTableWidget(0,7);t.setHorizontalHeaderLabels(['الرقم','الكود','الاسم','النوع','الهاتف','الرصيد','الحالة']);t.setSelectionBehavior(QAbstractItemView.SelectRows);t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents);t.horizontalHeader().setStretchLastSection(True);return t
    def load(self):self._load(self.customers,'customers','customer_code');self._load(self.suppliers,'suppliers','supplier_code')
    def _load(self,tbl,table,code):
        q=self.search.text().strip()
        with get_session() as s:
            names=cols(s,table);ce=f'"{code}"' if code in names else "''";rows=s.execute(text(f'SELECT id,{ce},name,COALESCE(party_type,\'\'),COALESCE(phone,\'\'),COALESCE(current_balance,0),COALESCE(is_active,1) FROM {table} WHERE :q=\'\' OR name LIKE :like OR {ce} LIKE :like OR COALESCE(phone,\'\') LIKE :like ORDER BY id DESC LIMIT 500'),{'q':q,'like':f'%{q}%'}).all()
        tbl.setRowCount(0)
        for x in rows:
            r=tbl.rowCount();tbl.insertRow(r)
            for c,v in enumerate(x):tbl.setItem(r,c,QTableWidgetItem('نشط' if c==6 and v else 'موقوف' if c==6 else display_value(v)))
    def selected(self):t=self.suppliers if self.tabs.currentIndex()==1 else self.customers;r=t.currentRow();return t,r
    def open_card(self):
        t,r=self.selected();
        if r<0:return QMessageBox.warning(self,'بطاقة','حدد سجلًا أولًا.')
        PartyCardDialog(int(t.item(r,0).text()),self.tabs.currentIndex()==1,self).exec()
    def add(self,supplier):
        table='suppliers' if supplier else 'customers';code='supplier_code' if supplier else 'customer_code';d=RecordDialog('إضافة '+('مورد' if supplier else 'عميل'),[{'name':x} for x in [code,'name','phone','email','address','tax_number','party_type','credit_limit','payment_terms','currency_code','is_active','notes']],parent=self)
        if d.exec()!=QDialog.Accepted:return
        v=d.values();v={k:x for k,x in v.items() if k in cols(get_session().__enter__(),table)} if False else v
        try:
            with get_session() as s:
                c=set(cols(s,table));v={k:x for k,x in v.items() if k in c};keys=list(v);s.execute(text(f'INSERT INTO {table} ({",".join(keys)}) VALUES ({",".join(":"+k for k in keys)})'),v);s.commit()
            self.load()
        except Exception as e:QMessageBox.critical(self,'فشل الحفظ',str(e))

class TreasuryOperationsWindow(QWidget):
    def __init__(self,user=None,parent=None):
        super().__init__(parent);self.user=user or {};self.setWindowTitle('الخزينة والصناديق');self.setMinimumSize(1250,760);self.setLayoutDirection(Qt.RightToLeft);self.setStyleSheet(APP_STYLE);root=QVBoxLayout(self);h=QHBoxLayout();h.addWidget(QLabel('الخزينة والصناديق'));h.addStretch()
        for cap,fn in [('سند قبض',self.receipt),('سند صرف',self.payment),('فتح وردية',self.open_session),('إغلاق وردية',self.close_session),('تحديث',self.load)]:b=QPushButton(cap);b.clicked.connect(fn);h.addWidget(b)
        root.addLayout(h);self.tabs=QTabWidget();root.addWidget(self.tabs,1);self.tables={}
        for cap,table in [('سندات القبض','cash_receipts'),('سندات الصرف','cash_payments'),('الورديات','cash_sessions'),('حركات الخزينة','cash_transactions')]:t=QTableWidget();self.tabs.addTab(t,cap);self.tables[table]=t
        self.load()
    def load(self):
        try:
            with get_session() as s:
                for table,t in self.tables.items():
                    if not exists(s,table):continue
                    names=cols(s,table)[:16];rows=s.execute(text(f'SELECT {",".join(chr(34)+n+chr(34) for n in names)} FROM {table} ORDER BY rowid DESC LIMIT 300')).all();t.setColumnCount(len(names));t.setHorizontalHeaderLabels([ar_field(n) for n in names]);t.setRowCount(0)
                    for x in rows:
                        r=t.rowCount();t.insertRow(r)
                        for c,v in enumerate(x):t.setItem(r,c,QTableWidgetItem(display_value(v)))
                    t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        except Exception as e:QMessageBox.critical(self,'الخزينة',str(e))
    def uid(self):return int(self.user.get('id') or 1)
    def receipt(self):
        cid,ok=QInputDialog.getInt(self,'سند قبض','رقم العميل:',1,1); 
        if not ok:return
        a,ok=QInputDialog.getDouble(self,'سند قبض','المبلغ:',0,0,999999999,2)
        if not ok:return
        try:PartyPaymentService.receive_from_customer(cid,a,'cash',cashier_id=self.uid());self.load()
        except Exception as e:QMessageBox.critical(self,'فشل القبض',str(e))
    def payment(self):
        sid,ok=QInputDialog.getInt(self,'سند صرف','رقم المورد:',1,1);
        if not ok:return
        a,ok=QInputDialog.getDouble(self,'سند صرف','المبلغ:',0,0,999999999,2)
        if not ok:return
        try:PartyPaymentService.pay_supplier(sid,a,'cash',cashier_id=self.uid());self.load()
        except Exception as e:QMessageBox.critical(self,'فشل الصرف',str(e))
    def open_session(self):
        a,ok=QInputDialog.getDouble(self,'فتح وردية','الرصيد الافتتاحي:',0,0,999999999,2)
        if not ok:return
        try:CashierSessionService.open(self.uid(),a,opened_by=self.uid())
        except PermissionError:
            with get_session() as s:s.execute(text("INSERT INTO cashier_sessions(cashier_id,opening_amount,status,opened_by) VALUES(:u,:a,'OPEN',:u)"),{'u':self.uid(),'a':a});s.commit()
        except Exception as e:return QMessageBox.critical(self,'فشل فتح الوردية',str(e))
        self.load()
    def close_session(self):
        with get_session() as s:row=s.execute(text("SELECT id FROM cashier_sessions WHERE cashier_id=:u AND status='OPEN' ORDER BY id DESC LIMIT 1"),{'u':self.uid()}).first()
        if not row:return QMessageBox.information(self,'الوردية','لا توجد وردية مفتوحة.')
        a,ok=QInputDialog.getDouble(self,'إغلاق وردية','النقد الفعلي:',0,0,999999999,2)
        if not ok:return
        try:CashierSessionService.close(row[0],a,closed_by=self.uid())
        except PermissionError:
            with get_session() as s:s.execute(text("UPDATE cashier_sessions SET closing_amount=:a,status='CLOSED',closed_at=CURRENT_TIMESTAMP,closed_by=:u WHERE id=:id"),{'a':a,'u':self.uid(),'id':row[0]});s.commit()
        except Exception as e:return QMessageBox.critical(self,'فشل إغلاق الوردية',str(e))
        self.load()

class TreasuryAccountsWindow(QWidget):
    def __init__(self,user=None,parent=None):
        super().__init__(parent);self.setWindowTitle('حسابات الخزينة والبنوك');self.setMinimumSize(1100,700);self.setLayoutDirection(Qt.RightToLeft);self.setStyleSheet(APP_STYLE);root=QVBoxLayout(self);h=QHBoxLayout();h.addWidget(QLabel('حسابات الخزينة والبنوك'));h.addStretch();
        for cap,fn in [('جديد',self.add),('فتح',self.statement),('تعديل',self.edit),('حذف',self.delete),('تحويل بين الحسابات',self.transfer),('تحديث',self.load)]:b=QPushButton(cap);b.clicked.connect(fn);h.addWidget(b)
        root.addLayout(h);self.table=QTableWidget();self.table.setSelectionBehavior(QAbstractItemView.SelectRows);root.addWidget(self.table,1);self.load()
    def load(self):
        try:rows=TreasuryOperationsService.list_accounts();self.table.setRowCount(0);self.table.setColumnCount(6);self.table.setHorizontalHeaderLabels(['الرقم','الرمز','الحساب','النوع','الحساب المحاسبي','الرصيد'])
        except Exception as e:return QMessageBox.critical(self,'الخزينة',str(e))
        for x in rows:
            r=self.table.rowCount();self.table.insertRow(r);vals=[x.get('id'),x.get('code'),x.get('name_ar'),x.get('account_type'),x.get('gl_account_code'),TreasuryOperationsService.balance(x['id'])]
            for c,v in enumerate(vals):self.table.setItem(r,c,QTableWidgetItem(str(v)))
    def selected(self):r=self.table.currentRow();return int(self.table.item(r,0).text()) if r>=0 else None
    def add(self):QMessageBox.information(self,'حساب خزينة','إضافة حساب خزينة تتم من بيانات الحسابات الأساسية المرتبطة بدليل الحسابات.')
    def edit(self):
        rid=self.selected();
        if rid is None:return
        QMessageBox.information(self,'تعديل','استخدم زر تعديل الحساب من دليل الحسابات للحفاظ على الربط المحاسبي.')
    def delete(self):
        rid=self.selected();
        if rid is None:return
        QMessageBox.information(self,'حذف','الحذف المباشر للحسابات المالية غير آمن؛ استخدم التعطيل من بطاقة الحساب.')
    def statement(self):
        rid=self.selected();
        if rid is None:return
        try:rows=TreasuryOperationsService.statement(rid,100);QMessageBox.information(self,'كشف الحساب','\n'.join(f"{x['created_at']} | {x['movement_type']} | {x['amount']:.2f}" for x in rows) or 'لا توجد حركات.')
        except Exception as e:QMessageBox.critical(self,'كشف الحساب',str(e))
    def transfer(self):
        try:rows=TreasuryOperationsService.list_accounts();
        except Exception as e:return QMessageBox.critical(self,'التحويل',str(e))
        if len(rows)<2:return QMessageBox.warning(self,'التحويل','يلزم حسابان على الأقل.')
        labels=[f"{x['id']} - {x['name_ar']}" for x in rows];a,ok=QInputDialog.getItem(self,'التحويل','من:',labels,0,False)
        if not ok:return
        b,ok=QInputDialog.getItem(self,'التحويل','إلى:',labels,1,False)
        if not ok:return
        amount,ok=QInputDialog.getDouble(self,'التحويل','المبلغ:',0,0.01,999999999,2)
        if not ok:return
        try:TreasuryOperationsService.transfer(int(a.split(' - ')[0]),int(b.split(' - ')[0]),amount,int(self.user.get('id') or 1),None);self.load()
        except Exception as e:QMessageBox.critical(self,'فشل التحويل',str(e))

class FinalSettingsWindow(QWidget):
    def __init__(self,user=None,parent=None):
        super().__init__(parent);self.setWindowTitle('الإعدادات');self.setMinimumSize(1100,760);self.setLayoutDirection(Qt.RightToLeft);self.setStyleSheet(APP_STYLE);root=QVBoxLayout(self);h=QHBoxLayout();h.addWidget(QLabel('الإعدادات'));h.addStretch();save=QPushButton('حفظ التغييرات');save.clicked.connect(self.save);h.addWidget(save);root.addLayout(h);body=QHBoxLayout();self.list=QListWidget();self.stack=QStackedWidget();body.addWidget(self.list);body.addWidget(self.stack,1);root.addLayout(body,1);self.fields={};self.add_page('المنشأة',[('company_name','اسم المنشأة'),('company_address','العنوان'),('company_phone','الهاتف'),('company_email','البريد الإلكتروني'),('company_tax','الرقم الضريبي')]);self.add_page('النظام',[('language','اللغة'),('direction','اتجاه الواجهة'),('base_currency','العملة الأساسية'),('default_tax_rate','نسبة الضريبة'),('date_format','تنسيق التاريخ'),('time_format','تنسيق الوقت')]);self.add_page('المبيعات',[('credit_sales_enabled','السماح بالبيع الآجل'),('customer_credit_limit_enabled','تفعيل حد الائتمان'),('price_override_requires_permission','تعديل السعر يتطلب صلاحية'),('discount_requires_permission','تعديل الخصم يتطلب صلاحية')]);self.add_page('المخزون',[('negative_stock_allowed','السماح بالمخزون السالب'),('stocktake_enabled','تفعيل الجرد'),('units_enabled','تفعيل الوحدات')]);self.add_page('الطباعة',[('printer_name','الطابعة'),('paper_size','مقاس الورق'),('invoice_template','قالب الفاتورة'),('invoice_customer_copy','نسخة العميل'),('company_logo_path','مسار الشعار')]);self.add_page('الأمان',[('session_minutes','مدة الجلسة بالدقائق'),('max_login_attempts','محاولات الدخول'),('password_policy','سياسة كلمة المرور')]);self.list.currentRowChanged.connect(self.stack.setCurrentIndex);self.load()
    def add_page(self,title,items):
        self.list.addItem(QListWidgetItem(title));w=QWidget();f=QFormLayout(w);f.setLabelAlignment(Qt.AlignRight);group=QGroupBox(title);gf=QFormLayout(group)
        for key,label in items:
            if key.endswith('_enabled') or key in {'negative_stock_allowed','stocktake_enabled','units_enabled','invoice_customer_copy','price_override_requires_permission','discount_requires_permission'}:q=QCheckBox()
            elif key in {'default_tax_rate'}:q=QDoubleSpinBox();q.setRange(0,100);q.setDecimals(2)
            elif key in {'session_minutes','max_login_attempts'}:q=QSpinBox();q.setRange(1,99999)
            else:q=QLineEdit()
            self.fields[key]=q;gf.addRow(label,q)
        f.addRow(group);self.stack.addWidget(w)
    def load(self):
        with get_session() as s:
            data={r[0]:r[1] for r in s.execute(text('SELECT setting_key,setting_value FROM system_settings')).all()};c=s.execute(text('SELECT name,address,phone,email,tax_number FROM companies ORDER BY id LIMIT 1')).first()
        if c:data.update({'company_name':c[0],'company_address':c[1],'company_phone':c[2],'company_email':c[3],'company_tax':c[4]})
        for k,w in self.fields.items():
            v=data.get(k,'')
            if isinstance(w,QCheckBox):w.setChecked(str(v).lower() in {'1','true','yes','نعم'})
            elif isinstance(w,(QSpinBox,QDoubleSpinBox)):
                try:w.setValue(float(v or 0))
                except:pass
            else:w.setText(str(v or ''))
    def value(self,w):
        if isinstance(w,QCheckBox):return '1' if w.isChecked() else '0'
        if isinstance(w,(QSpinBox,QDoubleSpinBox)):return str(w.value())
        return w.text().strip()
    def save(self):
        try:
            with get_session() as s:
                cid=s.execute(text('SELECT id FROM companies ORDER BY id LIMIT 1')).scalar()
                if cid:s.execute(text('UPDATE companies SET name=:n,address=:a,phone=:p,email=:e,tax_number=:t WHERE id=:id'),{'n':self.value(self.fields['company_name']),'a':self.value(self.fields['company_address']),'p':self.value(self.fields['company_phone']),'e':self.value(self.fields['company_email']),'t':self.value(self.fields['company_tax']),'id':cid})
                for k,w in self.fields.items():
                    if k.startswith('company_'):continue
                    v=self.value(w);rid=s.execute(text('SELECT id FROM system_settings WHERE setting_key=:k'),{'k':k}).scalar()
                    if rid:s.execute(text('UPDATE system_settings SET setting_value=:v WHERE id=:id'),{'v':v,'id':rid})
                    else:s.execute(text("INSERT INTO system_settings(setting_key,setting_value,value_type,description) VALUES(:k,:v,'text',:d)"),{'k':k,'v':v,'d':ar_field(k)})
                s.commit()
            QMessageBox.information(self,'تم الحفظ','تم حفظ الإعدادات بنجاح.')
        except Exception as e:QMessageBox.critical(self,'فشل الحفظ',str(e))

SettingsWindow=FinalSettingsWindow

def accounting_window(parent=None,user=None):
    w=QWidget(parent);w.setWindowTitle('المحاسبة العامة');w.setLayoutDirection(Qt.RightToLeft);w.setStyleSheet(APP_STYLE);l=QVBoxLayout(w);tabs=QTabWidget();l.addWidget(tabs)
    for table,title in [('journal_entries','القيود اليومية'),('journal_entry_lines','تفاصيل القيود'),('accounts','دليل الحسابات'),('chart_of_accounts','دليل الحسابات التفصيلي')]:tabs.addTab(AccessDataWindow(table,title,user=user,parent=w),title)
    return w

def employees_window(parent=None,user=None):
    w=QWidget(parent);w.setWindowTitle('الموارد البشرية');w.setLayoutDirection(Qt.RightToLeft);w.setStyleSheet(APP_STYLE);l=QVBoxLayout(w);tabs=QTabWidget();l.addWidget(tabs)
    for table,title in [('employees','الموظفون'),('employee_attendance','الحضور والانصراف'),('employee_leaves','الإجازات'),('payroll_periods','فترات الرواتب'),('payroll_runs','مسيرات الرواتب'),('payroll_items','تفاصيل الرواتب'),('users','المستخدمون'),('login_sessions','جلسات الدخول'),('roles','الأدوار'),('permissions','الصلاحيات')]:tabs.addTab(AccessDataWindow(table,title,user=user,parent=w),title)
    return w

def treasury_window(parent=None,user=None):return TreasuryOperationsWindow(user=user,parent=parent)
