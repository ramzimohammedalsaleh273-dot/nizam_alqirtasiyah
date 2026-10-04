from __future__ import annotations

from decimal import Decimal
from html import escape
from pathlib import Path
import os

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QIcon, QPixmap, QDesktopServices
from PySide6.QtPrintSupport import QPrintDialog, QPrinter, QPrinterInfo
from PySide6.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QToolButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMessageBox, QDialogButtonBox, QDoubleSpinBox,
    QSpinBox, QCheckBox, QComboBox, QTextEdit, QTabWidget, QFrame, QListWidget,
    QListWidgetItem, QCompleter, QFileDialog, QStackedWidget, QGroupBox,
    QScrollArea, QSizePolicy, QApplication
)
from PySide6.QtCore import QLocale
from sqlalchemy import text

from app.database.connection import get_session
from app.ui.theme import APP_STYLE
from app.ui.i18n import display_value


FIELD_LABELS = {
    'id':'الرقم','code':'الكود','name':'الاسم','name_ar':'الاسم بالعربية','name_en':'الاسم بالإنجليزية',
    'number':'الرقم','invoice_number':'رقم الفاتورة','request_number':'رقم الطلب','order_number':'رقم الأمر',
    'sku':'رمز الصنف','barcode':'الباركود','phone':'الهاتف','mobile':'الجوال','email':'البريد الإلكتروني',
    'address':'العنوان','tax_number':'الرقم الضريبي','commercial_number':'السجل التجاري','description':'الوصف','notes':'الملاحظات',
    'status':'الحالة','is_active':'نشط','created_at':'تاريخ الإنشاء','updated_at':'آخر تحديث','company_id':'الشركة','branch_id':'الفرع',
    'warehouse_id':'المستودع','category_id':'التصنيف','unit_id':'الوحدة','brand_id':'العلامة التجارية','parent_id':'الحساب الأب',
    'supplier_id':'المورد','customer_id':'العميل','employee_id':'الموظف','user_id':'المستخدم','role_id':'الدور','quantity':'الكمية',
    'reserved_quantity':'الكمية المحجوزة','available_quantity':'الكمية المتاحة','cost_price':'سعر التكلفة','sale_price':'سعر البيع',
    'wholesale_price':'سعر الجملة','school_price':'سعر المدارس','corporate_price':'سعر الشركات','min_price':'أقل سعر','min_stock':'الحد الأدنى',
    'max_stock':'الحد الأعلى','reorder_point':'نقطة إعادة الطلب','credit_limit':'حد الائتمان','current_balance':'الرصيد الحالي',
    'opening_balance':'الرصيد الافتتاحي','account_code':'رقم الحساب','account_name':'اسم الحساب','account_type':'نوع الحساب',
    'allow_posting':'يسمح بالترحيل','debit':'مدين','credit':'دائن','amount':'المبلغ','total_amount':'الإجمالي','subtotal':'الإجمالي قبل الضريبة',
    'discount_amount':'الخصم','tax_amount':'الضريبة','paid_amount':'المدفوع','due_amount':'المتبقي','invoice_date':'تاريخ الفاتورة',
    'payment_method':'طريقة الدفع','reference_number':'رقم المرجع','transaction_type':'نوع الحركة','movement_type':'نوع الحركة',
    'reference_type':'نوع المرجع','reference_id':'معرف المرجع','opened_at':'وقت الفتح','closed_at':'وقت الإغلاق',
    'expected_balance':'الرصيد المتوقع','actual_balance':'الرصيد الفعلي','difference':'الفرق','setting_key':'اسم الإعداد',
    'setting_value':'قيمة الإعداد','value_type':'نوع القيمة','document_no':'رقم المستند','document_type':'نوع المستند',
    'entity_type':'نوع الكيان','entity_id':'معرف الكيان','title':'العنوان','message':'الرسالة','read_at':'تاريخ القراءة','is_read':'مقروء',
    'payment_terms':'شروط السداد','currency_code':'رمز العملة','supplier_code':'رقم المورد','customer_code':'رقم العميل','employee_no':'رقم الموظف',
    'basic_salary':'الراتب الأساسي','salary':'الراتب','period_id':'الفترة','workflow_code':'رمز سير العمل','step_no':'رقم الخطوة',
    'step_name':'اسم الخطوة','role_code':'رمز الدور','template':'القالب','printer':'الطابعة','paper_size':'مقاس الورق','logo_path':'مسار الشعار'
}
TOKEN_LABELS = {
    'customer':'العميل','supplier':'المورد','product':'الصنف','item':'البند','employee':'الموظف','user':'المستخدم','company':'الشركة','branch':'الفرع',
    'warehouse':'المستودع','category':'التصنيف','unit':'الوحدة','account':'الحساب','quantity':'الكمية','price':'السعر','cost':'التكلفة',
    'total':'الإجمالي','subtotal':'الإجمالي الفرعي','discount':'الخصم','tax':'الضريبة','paid':'المدفوع','due':'المتبقي','balance':'الرصيد',
    'status':'الحالة','type':'النوع','description':'الوصف','notes':'الملاحظات','address':'العنوان','phone':'الهاتف','mobile':'الجوال',
    'email':'البريد الإلكتروني','barcode':'الباركود','sku':'رمز الصنف','salary':'الراتب','amount':'المبلغ','debit':'مدين','credit':'دائن',
    'reference':'المرجع','method':'الطريقة','payment':'الدفع','opening':'الافتتاحي','closing':'الإغلاق','difference':'الفرق','reserved':'المحجوز',
    'available':'المتاح','minimum':'الحد الأدنى','maximum':'الحد الأعلى','role':'الدور','permission':'الصلاحية','session':'الجلسة','login':'الدخول',
    'read':'القراءة','active':'نشط','enabled':'مفعل','parent':'الأب','period':'الفترة','workflow':'سير العمل','step':'الخطوة','request':'الطلب',
    'order':'الأمر','invoice':'الفاتورة','movement':'الحركة','transaction':'المعاملة','document':'المستند','message':'الرسالة','title':'العنوان',
    'value':'القيمة','setting':'الإعداد','currency':'العملة','country':'الدولة','language':'اللغة','printer':'الطابعة','template':'القالب','path':'المسار',
    'logo':'الشعار','paper':'الورق','created':'إنشاء','updated':'تحديث','date':'التاريخ','time':'الوقت','code':'الكود','name':'الاسم','number':'الرقم'
}
TABLE_TITLES = {
    'products':'المنتجات','customers':'العملاء','suppliers':'الموردون','product_categories':'التصنيفات','units':'الوحدات','warehouses':'المستودعات',
    'warehouse_zones':'مناطق التخزين','warehouse_aisles':'الممرات','warehouse_shelves':'الأرفف','warehouse_bins':'الخانات','stock_movements':'حركات المخزون',
    'stocktakes':'الجرد','accounts':'دليل الحسابات','chart_of_accounts':'دليل الحسابات التفصيلي','cash_registers':'الصناديق','cash_transactions':'حركات الخزينة',
    'cash_sessions':'الورديات','tax_rates':'الضرائب','tax_invoices':'الفواتير الضريبية','companies':'الشركات','branches':'الفروع','employees':'الموظفون',
    'departments':'الأقسام','job_positions':'الوظائف','employee_attendance':'الحضور والانصراف','employee_leaves':'الإجازات','payroll_periods':'فترات الرواتب',
    'payroll_runs':'مسيرات الرواتب','payroll_items':'تفاصيل الرواتب','users':'المستخدمون','login_sessions':'جلسات الدخول','roles':'الأدوار','permissions':'الصلاحيات',
    'erp_roles':'الأدوار','erp_permissions':'الصلاحيات','erp_login_sessions':'جلسات الدخول','printing_services':'خدمات الطباعة','printing_orders':'طلبات الطباعة',
    'approval_requests':'طلبات الاعتماد','audit_logs':'سجل التدقيق','audit_log':'سجل التدقيق','sync_queue':'المزامنة','sync_conflicts':'تعارضات المزامنة',
    'sync_devices':'أجهزة المزامنة','fiscal_periods':'الفترات المالية','journal_entries':'القيود اليومية','journal_entry_lines':'تفاصيل القيود',
    'notifications':'التنبيهات','documents':'المستندات','system_settings':'إعدادات النظام','document_sequences':'تسلسلات المستندات','sales':'المبيعات والفواتير',
    'purchase_invoices':'فواتير المشتريات','purchase_orders':'أوامر الشراء','purchase_requests':'طلبات الشراء'
}
LOOKUP_TABLES = {
    'company_id':'companies','branch_id':'branches','warehouse_id':'warehouses','category_id':'product_categories','unit_id':'units',
    'brand_id':'brands','supplier_id':'suppliers','customer_id':'customers','employee_id':'employees','user_id':'users','role_id':'roles','parent_id':'accounts'
}


def label(name: str) -> str:
    if name in FIELD_LABELS:
        return FIELD_LABELS[name]
    parts = name.lower().split('_')
    translated = ' '.join(TOKEN_LABELS.get(p, p) for p in parts)
    if all(p == TOKEN_LABELS.get(p, p) for p in parts) and any(p in TOKEN_LABELS for p in parts):
        return translated
    return translated.replace('_',' ')


def table_exists(session, name: str) -> bool:
    return bool(session.execute(text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:n"), {'n':name}).scalar())


def table_info(session, name: str):
    return session.connection().exec_driver_sql(f'PRAGMA table_info("{name}")').mappings().all()


def columns(session, name: str):
    return [r['name'] for r in table_info(session, name)]


def first_value(row, *names, default=None):
    for n in names:
        if n in row and row[n] not in (None, ''):
            return row[n]
    return default


def human_error(exc: Exception) -> str:
    msg = str(exc)
    replacements = {
        'no such column:':'العمود غير موجود في قاعدة البيانات:',
        'no such table:':'الجدول غير موجود في قاعدة البيانات:',
        'UNIQUE constraint failed:':'البيانات مكررة في حقل فريد:',
        'NOT NULL constraint failed:':'حقل إلزامي لم تتم تعبئته:',
        'FOREIGN KEY constraint failed':'البيانات مرتبطة بسجل آخر ولا يمكن تنفيذ العملية.',
        'database is locked':'قاعدة البيانات مشغولة حاليًا، أعد المحاولة بعد لحظات.'
    }
    for a,b in replacements.items():
        msg = msg.replace(a,b)
    return msg


class BackMixin:
    def setup_back(self, title_layout, text_value='رجوع'):
        b = QPushButton('←  ' + text_value)
        b.setObjectName('BackButton')
        b.setMinimumHeight(40)
        b.clicked.connect(self.close)
        title_layout.insertWidget(0, b)
        self.setAttribute(Qt.WA_DeleteOnClose, True)


class SearchableCombo(QComboBox):
    def __init__(self, items=None, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.NoInsert)
        if items:
            for text_value, data in items:
                self.addItem(text_value, data)
        comp = QCompleter(self.model(), self)
        comp.setCaseSensitivity(Qt.CaseInsensitive)
        comp.setFilterMode(Qt.MatchContains)
        comp.setCompletionMode(QCompleter.PopupCompletion)
        self.setCompleter(comp)


class RecordDialog(QDialog):
    def __init__(self, table_name, record=None, readonly=False, parent=None):
        super().__init__(parent)
        self.table_name = table_name
        self.record = dict(record or {})
        self.readonly = readonly
        self.widgets = {}
        self.setWindowTitle(('عرض — ' if readonly else 'تحرير — ') + TABLE_TITLES.get(table_name, label(table_name)))
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumSize(760, 560)
        self.setStyleSheet(APP_STYLE)
        root = QVBoxLayout(self)
        title_row = QHBoxLayout()
        title_row.addWidget(QLabel(TABLE_TITLES.get(table_name, label(table_name))))
        title_row.addStretch()
        root.addLayout(title_row)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        body = QWidget(); form = QFormLayout(body); form.setSpacing(12)
        with get_session() as s:
            info = table_info(s, table_name)
        for col in info:
            name = col['name']; typ = str(col['type'] or '').upper()
            if name in {'id','created_at','updated_at','last_login_at','read_at'} or name in {'password_hash','token_hash','session_token','secret','private_key','xml_content'}:
                continue
            required = bool(col['notnull']) and col['dflt_value'] is None
            w = self._widget(name, typ, self.record.get(name))
            if readonly:
                w.setEnabled(False)
            self.widgets[name] = w
            caption = label(name) + (' *' if required else '')
            form.addRow(caption, w)
        scroll.setWidget(body); root.addWidget(scroll, 1)
        buttons = QDialogButtonBox()
        if not readonly:
            buttons.addButton('حفظ', QDialogButtonBox.AcceptRole)
            buttons.addButton('إلغاء', QDialogButtonBox.RejectRole)
            buttons.accepted.connect(self._validate_and_accept)
        else:
            buttons.addButton('إغلاق', QDialogButtonBox.RejectRole)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _widget(self, name, typ, value):
        if name in LOOKUP_TABLES:
            w = SearchableCombo(); w.addItem('— اختر —', None)
            try:
                with get_session() as s:
                    t = LOOKUP_TABLES[name]
                    if table_exists(s, t):
                        cs = columns(s, t)
                        display = next((x for x in ('name_ar','name','title','code','number') if x in cs), 'id')
                        for row in s.execute(text(f'SELECT id,"{display}" FROM "{t}" ORDER BY id LIMIT 2000')).all():
                            w.addItem(f'{row[1]}  |  #{row[0]}', row[0])
                if value is not None:
                    idx = w.findData(value)
                    if idx >= 0: w.setCurrentIndex(idx)
            except Exception:
                pass
            return w
        if 'BOOL' in typ or name in {'is_active','is_read','allow_posting','is_locked','is_group','approved'}:
            w = QCheckBox('مفعل / نعم')
            w.setChecked(str(value).lower() in {'1','true','yes','نعم'}) if value is not None else w.setChecked(True)
            return w
        if any(x in typ for x in ('REAL','NUMERIC','DOUBLE','FLOAT','DECIMAL')):
            w = QDoubleSpinBox(); w.setRange(-999999999999999,999999999999999); w.setDecimals(3); w.setValue(float(value or 0)); return w
        if 'INT' in typ:
            w = QSpinBox(); w.setRange(-2147483648,2147483647); w.setValue(int(value or 0)); return w
        if name in {'description','notes','message','address','reason','remarks'}:
            w = QTextEdit(str(value or '')); w.setMinimumHeight(90); return w
        return QLineEdit('' if value is None else str(value))

    def _validate_and_accept(self):
        vals = self.values()
        with get_session() as s:
            for col in table_info(s, self.table_name):
                n = col['name']
                if col['notnull'] and col['dflt_value'] is None and n not in vals:
                    continue
                if col['notnull'] and col['dflt_value'] is None and vals.get(n) in (None, ''):
                    QMessageBox.warning(self, 'بيانات ناقصة', f'الحقل «{label(n)}» إلزامي.'); return
        self.accept()

    def values(self):
        out = {}
        for name,w in self.widgets.items():
            if isinstance(w, SearchableCombo): out[name] = w.currentData()
            elif isinstance(w, QCheckBox): out[name] = 1 if w.isChecked() else 0
            elif isinstance(w, QTextEdit): out[name] = w.toPlainText().strip() or None
            elif isinstance(w, (QSpinBox,QDoubleSpinBox)): out[name] = w.value()
            else: out[name] = w.text().strip() or None
        return out


class AccessDataWindow(QWidget, BackMixin):
    """جدول عربي حقيقي: بحث، فرز، فتح للعرض، تعديل، جديد، حذف، رجوع."""
    def __init__(self, table_name, title=None, columns=None, editable=True, user=None, parent=None):
        super().__init__(parent); self.table_name=table_name; self.title_text=title or TABLE_TITLES.get(table_name,label(table_name)); self.requested=columns; self.editable=editable; self.user=user or {}
        self.setWindowTitle(self.title_text); self.setMinimumSize(1280,760); self.setLayoutDirection(Qt.RightToLeft); self.setStyleSheet(APP_STYLE); self._build(); self._schema(); self.load()
    def _build(self):
        root=QVBoxLayout(self); root.setContentsMargins(18,16,18,16); root.setSpacing(12)
        top=QHBoxLayout(); self.setup_back(top); title=QLabel(self.title_text); title.setObjectName('PageTitle'); top.addWidget(title); top.addStretch(); self.count_label=QLabel(''); top.addWidget(self.count_label); root.addLayout(top)
        search_row=QHBoxLayout(); icon=QLabel('⌕'); icon.setObjectName('SearchIcon'); search_row.addWidget(icon); self.search=QLineEdit(); self.search.setObjectName('GlobalSearchBox'); self.search.setPlaceholderText(f'ابحث داخل {self.title_text} بالاسم أو الرقم أو الكود أو أي قيمة…'); self.search.textChanged.connect(lambda *_: self.load()); search_row.addWidget(self.search,1); clear=QPushButton('مسح'); clear.clicked.connect(self.search.clear); search_row.addWidget(clear); root.addLayout(search_row)
        actions=QHBoxLayout()
        for cap,fn in [('＋ جديد',self.add),('فتح السجل',self.open_record),('✎ تعديل',self.edit),('حذف',self.delete),('↻ تحديث',self.load)]:
            b=QPushButton(cap); b.setMinimumHeight(40); b.clicked.connect(fn); actions.addWidget(b)
        actions.addStretch(); root.addLayout(actions)
        self.table=QTableWidget(); self.table.setSelectionBehavior(QAbstractItemView.SelectRows); self.table.setSelectionMode(QAbstractItemView.SingleSelection); self.table.setEditTriggers(QAbstractItemView.NoEditTriggers); self.table.setAlternatingRowColors(True); self.table.setSortingEnabled(True); self.table.doubleClicked.connect(lambda *_: self.open_record()); root.addWidget(self.table,1)
        self.status=QLabel('جاهز'); root.addWidget(self.status)
    def _schema(self):
        with get_session() as s:
            if not table_exists(s,self.table_name): self.columns=[]; self.status.setText('هذا الجدول غير موجود في قاعدة البيانات.'); return
            names=columns(s,self.table_name)
        self.columns=[n for n in names if n not in {'password_hash','token_hash','session_token','secret','private_key','xml_content'}]
        if self.requested: self.columns=[n for n in self.columns if n in set(self.requested)]
        self.table.setColumnCount(len(self.columns)); self.table.setHorizontalHeaderLabels([label(n) for n in self.columns]); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive); self.table.horizontalHeader().setStretchLastSection(True)
    def _id(self):
        r=self.table.currentRow()
        if r<0: return None
        if 'id' in self.columns:
            try:return int(self.table.item(r,self.columns.index('id')).text())
            except:return None
        return None
    def load(self):
        if not self.columns:return
        q=self.search.text().strip(); params={}; where=''; searchable=[n for n in self.columns if n not in {'id','created_at','updated_at'}]
        if q and searchable:
            where=' WHERE '+' OR '.join(f'CAST("{n}" AS TEXT) LIKE :q' for n in searchable); params['q']=f'%{q}%'
        try:
            with get_session() as s: rows=s.execute(text(f'SELECT {",".join(chr(34)+n+chr(34) for n in self.columns)} FROM "{self.table_name}"{where} ORDER BY rowid DESC LIMIT 1000'),params).all()
            self.table.setSortingEnabled(False); self.table.setRowCount(0)
            for row in rows:
                r=self.table.rowCount(); self.table.insertRow(r)
                for c,v in enumerate(row): self.table.setItem(r,c,QTableWidgetItem(display_value(v)))
            self.table.setSortingEnabled(True); self.count_label.setText(f'{len(rows):,} سجل'); self.status.setText('تم تحديث البيانات بنجاح.')
        except Exception as exc: QMessageBox.critical(self,'تعذر تحميل الجدول',human_error(exc))
    def open_record(self):
        rid=self._id()
        if rid is None:return QMessageBox.information(self,'فتح السجل','حدد السجل الذي تريد فتحه أولًا.')
        with get_session() as s: rec=s.execute(text(f'SELECT * FROM "{self.table_name}" WHERE id=:id'),{'id':rid}).mappings().first()
        if rec: RecordDialog(self.table_name,rec,True,self).exec()
    def add(self):
        if not self.editable:return
        d=RecordDialog(self.table_name,parent=self)
        if d.exec()==QDialog.Accepted:self._write(d.values(),None)
    def edit(self):
        if not self.editable:return
        rid=self._id()
        if rid is None:return QMessageBox.information(self,'التعديل','حدد السجل الذي تريد تعديله أولًا.')
        with get_session() as s: rec=s.execute(text(f'SELECT * FROM "{self.table_name}" WHERE id=:id'),{'id':rid}).mappings().first()
        if rec:
            d=RecordDialog(self.table_name,rec,False,self)
            if d.exec()==QDialog.Accepted:self._write(d.values(),rid)
    def _write(self,values,rid):
        values={k:v for k,v in values.items() if k not in {'id','created_at','updated_at'}}
        try:
            with get_session() as s:
                if rid is None:
                    keys=[k for k,v in values.items() if v is not None]; params={k:values[k] for k in keys}; s.execute(text(f'INSERT INTO "{self.table_name}" ({",".join(chr(34)+k+chr(34) for k in keys)}) VALUES ({",".join(":"+k for k in keys)})'),params)
                else:
                    sets=[k for k in values if k not in {'id'}]; s.execute(text(f'UPDATE "{self.table_name}" SET {",".join(chr(34)+k+chr(34)+"= :"+k for k in sets)} WHERE id=:__id'),{**values,'__id':rid})
                s.commit()
            self.load()
        except Exception as exc: QMessageBox.critical(self,'فشل الحفظ',human_error(exc))
    def delete(self):
        rid=self._id()
        if rid is None:return QMessageBox.information(self,'الحذف','حدد السجل الذي تريد حذفه أولًا.')
        if QMessageBox.question(self,'تأكيد الحذف','هل أنت متأكد من حذف السجل؟\nسيتم منع الحذف إذا كان السجل مرتبطًا بمستندات أخرى.',QMessageBox.Yes|QMessageBox.No)==QMessageBox.Yes:
            try:
                with get_session() as s:s.execute(text(f'DELETE FROM "{self.table_name}" WHERE id=:id'),{'id':rid}); s.commit()
                self.load()
            except Exception as exc: QMessageBox.critical(self,'تعذر الحذف',human_error(exc))
    def export_data(self):
        path,_=QFileDialog.getSaveFileName(self,'تصدير الجدول','البيانات.xlsx','Excel (*.xlsx)')
        if not path:return
        try:
            from openpyxl import Workbook
            wb=Workbook(); ws=wb.active; ws.title=self.title_text[:31]; ws.append([label(n) for n in self.columns])
            for r in range(self.table.rowCount()): ws.append([self.table.item(r,c).text() if self.table.item(r,c) else '' for c in range(self.table.columnCount())])
            wb.save(path); QMessageBox.information(self,'تم التصدير','تم تصدير البيانات بنجاح.')
        except Exception as exc: QMessageBox.critical(self,'فشل التصدير',human_error(exc))
    def print_table(self):
        QMessageBox.information(self,'الطباعة','استخدم طباعة النظام من نافذة التقرير أو الفاتورة. سيتم ربط الطباعة المتخصصة حسب نوع الجدول.')


class InvoiceViewDialog(QDialog):
    def __init__(self, kind, document_id, parent=None):
        super().__init__(parent); self.kind=kind; self.document_id=int(document_id); self.html=''; self.setWindowTitle('الفاتورة الأصلية'); self.setMinimumSize(900,720); self.setLayoutDirection(Qt.RightToLeft); self.setStyleSheet(APP_STYLE)
        root=QVBoxLayout(self); top=QHBoxLayout(); back=QPushButton('← رجوع'); back.clicked.connect(self.reject); top.addWidget(back); title=QLabel('فاتورة بيع أصلية' if kind=='sale' else 'فاتورة شراء أصلية'); title.setObjectName('PageTitle'); top.addWidget(title); top.addStretch(); root.addLayout(top)
        from PySide6.QtWidgets import QTextBrowser
        self.browser=QTextBrowser(); self.browser.setOpenExternalLinks(True); root.addWidget(self.browser,1)
        buttons=QHBoxLayout(); p=QPushButton('🖨 إخراج / طباعة'); p.clicked.connect(self.print_invoice); close=QPushButton('إغلاق'); close.clicked.connect(self.reject); buttons.addStretch(); buttons.addWidget(p); buttons.addWidget(close); root.addLayout(buttons)
        try:self.html=self.build_html(); self.browser.setHtml(self.html)
        except Exception as exc:self.browser.setHtml(f'<h3>تعذر بناء الفاتورة</h3><p>{escape(human_error(exc))}</p>')
    def _company(self,s):
        if not table_exists(s,'companies'):return ('نظام القرطاسية','','')
        cs=columns(s,'companies'); display=next((x for x in ('name_ar','name','name_en') if x in cs),'id'); row=s.execute(text(f'SELECT "{display}" FROM companies ORDER BY id LIMIT 1')).first(); return (str(row[0]) if row else 'نظام القرطاسية','','')
    def build_html(self):
        main='sales' if self.kind=='sale' else 'purchase_invoices'; item_table='sale_items' if self.kind=='sale' else ('purchase_invoice_items' if table_exists(self._session_probe(),'purchase_invoice_items') else 'purchase_items')
        with get_session() as s:
            cs=columns(s,main); item_exists=table_exists(s,item_table)
            number_col=next((x for x in ('invoice_number','number','document_no') if x in cs),'id'); customer_col='customer_id' if 'customer_id' in cs else ('supplier_id' if 'supplier_id' in cs else None)
            fields=[x for x in ('created_at','invoice_date','subtotal','discount_amount','tax_amount','total_amount','paid_amount','due_amount','status') if x in cs]
            select=', '.join([f'"{x}"' for x in [number_col]+fields])
            row=s.execute(text(f'SELECT {select} FROM "{main}" WHERE id=:id LIMIT 1'),{'id':self.document_id}).mappings().first()
            if not row:raise ValueError('المستند غير موجود.')
            party='';
            if customer_col:
                table='customers' if customer_col=='customer_id' else 'suppliers'
                if table_exists(s,table):
                    pcols=columns(s,table); pn=next((x for x in ('name_ar','name','name_en') if x in pcols),'id'); party=s.execute(text(f'SELECT "{pn}" FROM "{table}" WHERE id=:id'),{'id':row.get(customer_col)}).scalar() if row.get(customer_col) else ''
            items=[]
            if item_exists:
                ics=columns(s,item_table); fk='sale_id' if self.kind=='sale' and 'sale_id' in ics else ('purchase_invoice_id' if 'purchase_invoice_id' in ics else ('purchase_id' if 'purchase_id' in ics else None))
                if fk:
                    pn='product_id' if 'product_id' in ics else None
                    for x in s.execute(text(f'SELECT * FROM "{item_table}" WHERE "{fk}"=:id ORDER BY id'),{'id':self.document_id}).mappings().all():
                        product='';
                        if pn and table_exists(s,'products'):
                            pcols=columns(s,'products'); pc=next((z for z in ('name_ar','name','name_en','sku') if z in pcols),'id'); product=s.execute(text(f'SELECT "{pc}" FROM products WHERE id=:id'),{'id':x.get(pn)}).scalar() or x.get(pn)
                        items.append((product, first_value(x,'quantity',default=0), first_value(x,'unit_price','unit_cost','price',default=0), first_value(x,'discount_amount',default=0), first_value(x,'tax_amount',default=0), first_value(x,'line_total','total_amount',default=0)))
            company=self._company(s)[0]
        rows=''.join(f'<tr><td>{escape(str(a))}</td><td>{b}</td><td>{Decimal(str(c or 0)):.2f}</td><td>{Decimal(str(d or 0)):.2f}</td><td>{Decimal(str(e or 0)):.2f}</td><td>{Decimal(str(f or 0)):.2f}</td></tr>' for a,b,c,d,e,f in items)
        title='فاتورة بيع أصلية' if self.kind=='sale' else 'فاتورة شراء أصلية'
        return f'''<html><body dir="rtl" style="font-family:Tahoma,Arial;background:#fff;color:#172033;padding:20px"><div style="border:2px solid #172033;border-radius:12px;padding:18px"><div style="text-align:center"><h1>{escape(company)}</h1><h2>{title}</h2><div style="font-size:18px;font-weight:bold">{escape(str(row[number_col]))}</div></div><hr><table width="100%"><tr><td><b>التاريخ:</b> {escape(str(first_value(row,'invoice_date','created_at',default='')))}</td><td><b>{'العميل' if self.kind=='sale' else 'المورد'}:</b> {escape(str(party or 'غير محدد'))}</td><td><b>الحالة:</b> {escape(str(row.get('status') or ''))}</td></tr></table><br><table border="1" cellspacing="0" cellpadding="8" width="100%"><tr style="font-weight:bold"><th>الصنف</th><th>الكمية</th><th>سعر الوحدة</th><th>الخصم</th><th>الضريبة</th><th>الإجمالي</th></tr>{rows}</table><br><table align="left" cellpadding="8"><tr><td>الإجمالي قبل الضريبة</td><td>{Decimal(str(row.get('subtotal') or 0)):.2f}</td></tr><tr><td>الخصم</td><td>{Decimal(str(row.get('discount_amount') or 0)):.2f}</td></tr><tr><td>الضريبة</td><td>{Decimal(str(row.get('tax_amount') or 0)):.2f}</td></tr><tr style="font-size:18px;font-weight:bold"><td>الإجمالي النهائي</td><td>{Decimal(str(row.get('total_amount') or 0)):.2f}</td></tr><tr><td>المدفوع</td><td>{Decimal(str(row.get('paid_amount') or 0)):.2f}</td></tr><tr><td>المتبقي</td><td>{Decimal(str(row.get('due_amount') or 0)):.2f}</td></tr></table><div style="clear:both;text-align:center;margin-top:90px;color:#667085">شكرًا لتعاملكم معنا — نظام القرطاسية</div></div></body></html>'''
    def _session_probe(self):
        return get_session().__enter__()
    def print_invoice(self):
        printer=QPrinter(QPrinter.HighResolution); dialog=QPrintDialog(printer,self)
        if dialog.exec()!=QDialog.Accepted:return
        from PySide6.QtGui import QTextDocument
        doc=QTextDocument(); doc.setHtml(self.html); doc.print_(printer)


class SalesWindow(QWidget, BackMixin):
    def __init__(self,user=None,parent=None):
        super().__init__(parent); self.user=user or {}; self.setWindowTitle('المبيعات والفواتير'); self.setMinimumSize(1250,760); self.setLayoutDirection(Qt.RightToLeft); self.setStyleSheet(APP_STYLE); self._build(); self.load()
    def _build(self):
        root=QVBoxLayout(self); top=QHBoxLayout(); self.setup_back(top); top.addWidget(QLabel('المبيعات والفواتير')); top.addStretch(); root.addLayout(top)
        bar=QHBoxLayout(); self.search=QLineEdit(); self.search.setPlaceholderText('ابحث برقم الفاتورة أو اسم العميل أو الحالة…'); self.search.textChanged.connect(lambda *_:self.load()); bar.addWidget(self.search,1); root.addLayout(bar)
        actions=QHBoxLayout();
        for cap,fn in [('فتح الفاتورة الأصلية',self.open_selected),('حذف',self.delete_selected),('تحديث',self.load)]: b=QPushButton(cap); b.clicked.connect(fn); actions.addWidget(b)
        actions.addStretch(); root.addLayout(actions)
        self.table=QTableWidget(); self.table.setSelectionBehavior(QAbstractItemView.SelectRows); self.table.setSelectionMode(QAbstractItemView.SingleSelection); self.table.setSortingEnabled(True); self.table.doubleClicked.connect(lambda *_:self.open_selected()); root.addWidget(self.table,1)
    def load(self):
        with get_session() as s:
            if not table_exists(s,'sales'):return
            cs=columns(s,'sales'); self.cols=[x for x in ('id','invoice_number','created_at','subtotal','discount_amount','tax_amount','total_amount','paid_amount','due_amount','status','customer_id') if x in cs]; q=self.search.text().strip(); params={}; where=''
            if q:
                ors=[f'CAST(s."{x}" AS TEXT) LIKE :q' for x in self.cols if x!='id' and x!='customer_id']; ors.append("CAST(COALESCE(c.name_ar,c.name,c.name_en,'') AS TEXT) LIKE :q"); where=' WHERE '+' OR '.join(ors); params['q']=f'%{q}%'
            rows=s.execute(text(f'SELECT s."{self.cols[0]}" AS id, s.invoice_number, s.created_at, s.subtotal, s.discount_amount, s.tax_amount, s.total_amount, s.paid_amount, s.due_amount, s.status, COALESCE(c.name_ar,c.name,c.name_en,\'بدون عميل\') AS customer FROM sales s LEFT JOIN customers c ON c.id=s.customer_id{where} ORDER BY s.id DESC LIMIT 1000'),params).all()
        headers=['id','invoice_number','created_at','subtotal','discount_amount','tax_amount','total_amount','paid_amount','due_amount','status','customer']; labels=['الرقم','رقم الفاتورة','التاريخ','قبل الضريبة','الخصم','الضريبة','الإجمالي','المدفوع','المتبقي','الحالة','العميل']; self.table.setColumnCount(len(headers)); self.table.setHorizontalHeaderLabels(labels); self.table.setRowCount(0)
        for row in rows:
            r=self.table.rowCount(); self.table.insertRow(r)
            for c,v in enumerate(row):self.table.setItem(r,c,QTableWidgetItem(display_value(v)))
        self.table.horizontalHeader().setStretchLastSection(True)
    def selected_id(self):
        r=self.table.currentRow();
        if r<0:return None
        try:return int(self.table.item(r,0).text())
        except:return None
    def open_selected(self):
        rid=self.selected_id();
        if rid is None:return QMessageBox.information(self,'فتح الفاتورة','حدد فاتورة أولًا.')
        d=InvoiceViewDialog('sale',rid,self); d.exec()
    def delete_selected(self):
        QMessageBox.information(self,'حذف الفاتورة','الفواتير المرحّلة لا تُحذف مباشرة. استخدم الإلغاء أو المرتجع للحفاظ على السجل المحاسبي.')


class PurchasesWindow(SalesWindow):
    def __init__(self,user=None,parent=None):
        QWidget.__init__(self,parent); self.user=user or {}; self.setWindowTitle('المشتريات وفواتير الشراء'); self.setMinimumSize(1250,760); self.setLayoutDirection(Qt.RightToLeft); self.setStyleSheet(APP_STYLE); self._build_purchase(); self.load_purchase()
    def _build_purchase(self):
        root=QVBoxLayout(self); top=QHBoxLayout(); self.setup_back(top); top.addWidget(QLabel('المشتريات وفواتير الشراء')); top.addStretch(); root.addLayout(top); bar=QHBoxLayout(); self.search=QLineEdit(); self.search.setPlaceholderText('ابحث برقم فاتورة الشراء أو اسم المورد…'); self.search.textChanged.connect(lambda *_:self.load_purchase()); bar.addWidget(self.search,1); root.addLayout(bar); actions=QHBoxLayout();
        for cap,fn in [('فتح الفاتورة الأصلية',self.open_purchase),('جديد',self.new_purchase),('تحديث',self.load_purchase)]:b=QPushButton(cap);b.clicked.connect(fn);actions.addWidget(b)
        actions.addStretch();root.addLayout(actions);self.table=QTableWidget();self.table.setSelectionBehavior(QAbstractItemView.SelectRows);self.table.setSelectionMode(QAbstractItemView.SingleSelection);self.table.doubleClicked.connect(lambda *_:self.open_purchase());root.addWidget(self.table,1)
    def load_purchase(self):
        with get_session() as s:
            if not table_exists(s,'purchase_invoices'):self.table.setRowCount(0);return
            cs=columns(s,'purchase_invoices'); number=next((x for x in ('invoice_number','number','document_no') if x in cs),'id'); supplier='supplier_id' if 'supplier_id' in cs else None; q=self.search.text().strip(); params={}; where=''
            if q:
                ors=[f'CAST(p."{x}" AS TEXT) LIKE :q' for x in cs if x not in {'id'}];
                if supplier and table_exists(s,'suppliers'):ors.append("COALESCE(sp.name_ar,sp.name,sp.name_en,'') LIKE :q"); where=' WHERE '+' OR '.join(ors); params['q']=f'%{q}%'
            join=" LEFT JOIN suppliers sp ON sp.id=p.supplier_id" if supplier and table_exists(s,'suppliers') else ''
            wanted=[x for x in ('id',number,'created_at','subtotal','discount_amount','tax_amount','total_amount','paid_amount','due_amount','status') if x in cs]; rows=s.execute(text(f'SELECT p."{wanted[0]}" AS id, '+','.join(f'p."{x}"' for x in wanted[1:])+f", COALESCE(sp.name_ar,sp.name,sp.name_en,'غير محدد') AS supplier FROM purchase_invoices p{join}{where} ORDER BY p.id DESC LIMIT 1000"),params).all()
        labels=['الرقم','رقم الفاتورة','التاريخ','قبل الضريبة','الخصم','الضريبة','الإجمالي','المدفوع','المتبقي','الحالة','المورد']; self.table.setColumnCount(len(labels));self.table.setHorizontalHeaderLabels(labels);self.table.setRowCount(0)
        for row in rows:
            r=self.table.rowCount();self.table.insertRow(r)
            for c,v in enumerate(row):self.table.setItem(r,c,QTableWidgetItem(display_value(v)))
    def open_purchase(self):
        r=self.table.currentRow();
        if r<0:return QMessageBox.information(self,'فتح الفاتورة','حدد فاتورة أولًا.')
        try:rid=int(self.table.item(r,0).text())
        except:return
        InvoiceViewDialog('purchase',rid,self).exec()
    def new_purchase(self):
        QMessageBox.information(self,'فاتورة شراء جديدة','لإنشاء فاتورة شراء استخدم دورة المشتريات؛ بعد الاستلام ستظهر هنا الفاتورة الأصلية المحفوظة.')


class ProductCardDialog(RecordDialog):
    pass


class InventoryWindow(QWidget, BackMixin):
    def __init__(self,user=None,parent=None):
        super().__init__(parent); self.user=user or {}; self.setWindowTitle('المنتجات والمخزون'); self.setMinimumSize(1280,760); self.setLayoutDirection(Qt.RightToLeft); self.setStyleSheet(APP_STYLE); root=QVBoxLayout(self); top=QHBoxLayout(); self.setup_back(top); top.addWidget(QLabel('المنتجات والمخزون')); top.addStretch(); root.addLayout(top); bar=QHBoxLayout(); self.search=QLineEdit();self.search.setPlaceholderText('ابحث باسم الصنف أو الرمز أو الباركود…');self.search.textChanged.connect(lambda *_:self.load());bar.addWidget(self.search,1);root.addLayout(bar);acts=QHBoxLayout();
        for cap,fn in [('＋ إضافة منتج',self.add_product),('فتح البطاقة',self.open_product),('✎ تعديل',self.edit_product),('حذف',self.delete_product),('تحديث',self.load)]:b=QPushButton(cap);b.clicked.connect(fn);acts.addWidget(b)
        acts.addStretch();root.addLayout(acts);self.table=QTableWidget();self.table.setSelectionBehavior(QAbstractItemView.SelectRows);self.table.setSelectionMode(QAbstractItemView.SingleSelection);self.table.doubleClicked.connect(lambda *_:self.open_product());root.addWidget(self.table,1);self.load()
    def load(self):
        with get_session() as s:
            if not table_exists(s,'products'):return
            cs=columns(s,'products'); wanted=[x for x in ('id','sku','barcode','name_ar','name','cost_price','sale_price','wholesale_price','school_price','quantity','available_quantity') if x in cs]; q=self.search.text().strip();params={};where=''
            if q:
                where=' WHERE '+' OR '.join(f'CAST("{x}" AS TEXT) LIKE :q' for x in wanted if x!='id');params['q']=f'%{q}%'
            rows=s.execute(text(f'SELECT {",".join(chr(34)+x+chr(34) for x in wanted)} FROM products{where} ORDER BY id DESC LIMIT 1500'),params).all()
        self.cols=wanted; self.table.setColumnCount(len(wanted));self.table.setHorizontalHeaderLabels([label(x) for x in wanted]);self.table.setRowCount(0)
        for row in rows:
            r=self.table.rowCount();self.table.insertRow(r)
            for c,v in enumerate(row):self.table.setItem(r,c,QTableWidgetItem(display_value(v)))
        self.table.horizontalHeader().setStretchLastSection(True)
    def pid(self):
        r=self.table.currentRow();
        if r<0:return None
        try:return int(self.table.item(r,self.cols.index('id')).text())
        except:return None
    def add_product(self):
        d=RecordDialog('products',parent=self)
        if d.exec()==QDialog.Accepted:self.write_product(d.values())
    def open_product(self):
        rid=self.pid();
        if rid is None:return QMessageBox.information(self,'بطاقة الصنف','حدد صنفًا أولًا.')
        with get_session() as s: rec=s.execute(text('SELECT * FROM products WHERE id=:id'),{'id':rid}).mappings().first()
        if rec: RecordDialog('products',rec,True,self).exec()
    def edit_product(self):
        rid=self.pid();
        if rid is None:return QMessageBox.information(self,'تعديل الصنف','حدد صنفًا أولًا.')
        with get_session() as s: rec=s.execute(text('SELECT * FROM products WHERE id=:id'),{'id':rid}).mappings().first()
        if not rec:return
        d=RecordDialog('products',rec,False,self)
        if d.exec()==QDialog.Accepted:self.write_product(d.values(),rid)
    def write_product(self,values,rid=None):
        values={k:v for k,v in values.items() if k not in {'id','created_at','updated_at'}}
        try:
            with get_session() as s:
                if rid is None:
                    keys=[k for k,v in values.items() if v is not None];s.execute(text(f'INSERT INTO products ({",".join(chr(34)+k+chr(34) for k in keys)}) VALUES ({",".join(":"+k for k in keys)})'),{k:values[k] for k in keys})
                else:s.execute(text(f'UPDATE products SET {",".join(chr(34)+k+chr(34)+"=:"+k for k in values)} WHERE id=:id'),{**values,'id':rid})
                s.commit()
            self.load();QMessageBox.information(self,'تم حفظ المنتج','تم حفظ الصنف بنجاح. يمكنك الآن متابعة العمل.')
        except Exception as exc:QMessageBox.critical(self,'لم يتم حفظ المنتج',human_error(exc))
    def delete_product(self):
        QMessageBox.information(self,'حذف الصنف','إذا كان الصنف مستخدمًا في فواتير أو حركات فلن نحذفه حفاظًا على التاريخ. استخدم التعطيل بدل الحذف.')


class PartyProfileDialog(QDialog):
    def __init__(self, party_type, party_id, parent=None):
        super().__init__(parent); self.party_type=party_type;self.party_id=int(party_id);self.setWindowTitle('ملف العميل' if party_type=='customer' else 'ملف المورد');self.setMinimumSize(1100,720);self.setLayoutDirection(Qt.RightToLeft);self.setStyleSheet(APP_STYLE);root=QVBoxLayout(self);top=QHBoxLayout();b=QPushButton('← رجوع');b.clicked.connect(self.reject);top.addWidget(b);self.title=QLabel('الملف الكامل');top.addWidget(self.title);top.addStretch();root.addLayout(top);self.tabs=QTabWidget();root.addWidget(self.tabs,1);self.build()
    def build(self):
        table='customers' if self.party_type=='customer' else 'suppliers'; sale_table='sales' if self.party_type=='customer' else 'purchase_invoices'; fk='customer_id' if self.party_type=='customer' else 'supplier_id'
        with get_session() as s:
            rec=s.execute(text(f'SELECT * FROM {table} WHERE id=:id'),{'id':self.party_id}).mappings().first()
            if not rec:raise ValueError('السجل غير موجود')
            self.title.setText(str(first_value(rec,'name_ar','name','name_en',default='الملف')))
            details=QTableWidget(0,2);details.setHorizontalHeaderLabels(['البيان','القيمة']);
            for k,v in rec.items():
                r=details.rowCount();details.insertRow(r);details.setItem(r,0,QTableWidgetItem(label(k)));details.setItem(r,1,QTableWidgetItem(display_value(v)))
            self.tabs.addTab(details,'البيانات الأساسية')
            if table_exists(s,sale_table):
                cs=columns(s,sale_table); number=next((x for x in ('invoice_number','number','document_no') if x in cs),'id'); rows=s.execute(text(f'SELECT id,"{number}",created_at,total_amount,paid_amount,due_amount,status FROM {sale_table} WHERE {fk}=:id ORDER BY id DESC LIMIT 200'),{'id':self.party_id}).all()
                t=QTableWidget(0,7);t.setHorizontalHeaderLabels(['الرقم','رقم الفاتورة','التاريخ','الإجمالي','المدفوع','المتبقي','الحالة']);
                for row in rows:
                    r=t.rowCount();t.insertRow(r)
                    for c,v in enumerate(row):t.setItem(r,c,QTableWidgetItem(display_value(v)))
                t.cellDoubleClicked.connect(lambda r,c,tt=t:self.open_invoice(tt,r));self.tabs.addTab(t,'الفواتير الأصلية')
    def open_invoice(self,t,r):
        try:rid=int(t.item(r,0).text()); InvoiceViewDialog('sale' if self.party_type=='customer' else 'purchase',rid,self).exec()
        except Exception as exc:QMessageBox.critical(self,'تعذر فتح الفاتورة',human_error(exc))


class PartiesWindow(QWidget, BackMixin):
    def __init__(self,user=None,parent=None):
        super().__init__(parent);self.user=user or {};self.setWindowTitle('العملاء والموردون');self.setMinimumSize(1250,760);self.setLayoutDirection(Qt.RightToLeft);self.setStyleSheet(APP_STYLE);root=QVBoxLayout(self);top=QHBoxLayout();self.setup_back(top);top.addWidget(QLabel('العملاء والموردون'));top.addStretch();root.addLayout(top);self.tabs=QTabWidget();root.addWidget(self.tabs,1);self.customer=self._make('customers','العملاء');self.supplier=self._make('suppliers','الموردون');self.tabs.addTab(self.customer,'العملاء');self.tabs.addTab(self.supplier,'الموردون')
    def _make(self,table,title):
        w=QWidget();root=QVBoxLayout(w);bar=QHBoxLayout();search=QLineEdit();search.setPlaceholderText('بحث بالاسم أو الهاتف أو الكود…');bar.addWidget(search,1);root.addLayout(bar);t=QTableWidget();t.setSelectionBehavior(QAbstractItemView.SelectRows);t.setSelectionMode(QAbstractItemView.SingleSelection);root.addWidget(t,1);actions=QHBoxLayout();openb=QPushButton('فتح الملف الكامل');newb=QPushButton('＋ جديد');editb=QPushButton('✎ تعديل');refresh=QPushButton('↻ تحديث');
        for b in (openb,newb,editb,refresh):actions.addWidget(b)
        actions.addStretch();root.addLayout(actions)
        def load():
            with get_session() as s:
                cs=columns(s,table); wanted=[x for x in ('id','code','name_ar','name','phone','mobile','email','tax_number','current_balance','status') if x in cs];q=search.text().strip();params={};where=''
                if q:where=' WHERE '+' OR '.join(f'CAST("{x}" AS TEXT) LIKE :q' for x in wanted if x!='id');params['q']=f'%{q}%'
                rows=s.execute(text(f'SELECT {",".join(chr(34)+x+chr(34) for x in wanted)} FROM {table}{where} ORDER BY id DESC LIMIT 1000'),params).all()
            t.setColumnCount(len(wanted));t.setHorizontalHeaderLabels([label(x) for x in wanted]);t.setRowCount(0);t._modern_cols=wanted
            for row in rows:
                r=t.rowCount();t.insertRow(r)
                for c,v in enumerate(row):t.setItem(r,c,QTableWidgetItem(display_value(v)))
        def selected():
            r=t.currentRow();
            if r<0:return None
            try:return int(t.item(r,0).text())
            except:return None
        def open_card():
            rid=selected()
            if rid is None:return QMessageBox.information(w,'فتح الملف','حدد العميل أو المورد أولًا.')
            PartyProfileDialog('customer' if table=='customers' else 'supplier',rid,w).exec()
        def add():
            d=RecordDialog(table,parent=w)
            if d.exec()==QDialog.Accepted:
                AccessDataWindow(table,title,editable=True,parent=w)._write(d.values(),None);load()
        def edit():
            rid=selected();
            if rid is None:return
            with get_session() as s:rec=s.execute(text(f'SELECT * FROM {table} WHERE id=:id'),{'id':rid}).mappings().first()
            if rec:
                d=RecordDialog(table,rec,False,w)
                if d.exec()==QDialog.Accepted:AccessDataWindow(table,title,editable=True,parent=w)._write(d.values(),rid);load()
        openb.clicked.connect(open_card);newb.clicked.connect(add);editb.clicked.connect(edit);refresh.clicked.connect(load);search.textChanged.connect(lambda *_:load());t.doubleClicked.connect(lambda *_:open_card());load();return w


class TreasuryOperationsWindow(QWidget, BackMixin):
    def __init__(self,user=None,parent=None):
        super().__init__(parent);self.user=user or {};self.setWindowTitle('الخزينة');self.setMinimumSize(1200,760);self.setLayoutDirection(Qt.RightToLeft);self.setStyleSheet(APP_STYLE);root=QVBoxLayout(self);top=QHBoxLayout();self.setup_back(top);top.addWidget(QLabel('الخزينة وحركة النقد'));top.addStretch();root.addLayout(top);actions=QHBoxLayout();
        for cap,kind in [('＋ سند قبض','قبض'),('＋ سند صرف','صرف')]:b=QPushButton(cap);b.setMinimumHeight(48);b.clicked.connect(lambda _,k=kind:self.voucher(k));actions.addWidget(b)
        actions.addStretch();root.addLayout(actions);self.tabs=QTabWidget();root.addWidget(self.tabs,1);self.load_tabs()
    def load_tabs(self):
        with get_session() as s:
            if not table_exists(s,'treasury_movements'):return
            cs=columns(s,'treasury_movements');rows=s.execute(text('SELECT * FROM treasury_movements ORDER BY id DESC LIMIT 500')).mappings().all()
        t=QTableWidget(0,len(cs));t.setHorizontalHeaderLabels([label(x) for x in cs]);
        for row in rows:
            r=t.rowCount();t.insertRow(r)
            for c,k in enumerate(cs):t.setItem(r,c,QTableWidgetItem(display_value(row[k])))
        self.tabs.addTab(t,'الحركات');
    def voucher(self,kind):
        d=VoucherDialog(kind,self)
        if d.exec()!=QDialog.Accepted:return
        try:
            from app.services.treasury_operations_service import TreasuryOperationsService
            data=d.values();uid=self.user.get('id') or self.user.get('user_id')
            if kind=='قبض':TreasuryOperationsService.create_receipt(**data,user_id=uid)
            else:TreasuryOperationsService.create_payment(**data,user_id=uid)
            QMessageBox.information(self,'تم الحفظ',f'تم حفظ سند {kind} في الخزينة.');self.tabs.clear();self.load_tabs()
        except Exception as exc:QMessageBox.critical(self,'تعذر حفظ السند',human_error(exc))


class VoucherDialog(QDialog):
    def __init__(self,kind,parent=None):
        super().__init__(parent);self.kind=kind;self.setWindowTitle('سند '+kind);self.setMinimumSize(600,460);self.setLayoutDirection(Qt.RightToLeft);self.setStyleSheet(APP_STYLE);root=QVBoxLayout(self);title=QLabel('إنشاء سند '+kind);title.setObjectName('PageTitle');root.addWidget(title);form=QFormLayout();self.amount=QDoubleSpinBox();self.amount.setRange(0,999999999999);self.amount.setDecimals(2);self.amount.setMinimumHeight(44);self.reference=QLineEdit();self.notes=QTextEdit();self.notes.setMinimumHeight(100);form.addRow('المبلغ *',self.amount);form.addRow('المرجع',self.reference);form.addRow('البيان',self.notes);root.addLayout(form);bb=QDialogButtonBox();bb.addButton('حفظ السند',QDialogButtonBox.AcceptRole);bb.addButton('إلغاء',QDialogButtonBox.RejectRole);bb.accepted.connect(self.accept);bb.rejected.connect(self.reject);root.addWidget(bb)
    def values(self):return {'amount':self.amount.value(),'reference':self.reference.text().strip() or None,'description':self.notes.toPlainText().strip() or None}


class UniversalSearchWindow(QWidget, BackMixin):
    def __init__(self,parent=None):
        super().__init__(parent);self.setWindowTitle('البحث العام — مركز الوصول السريع');self.setMinimumSize(1380,820);self.setLayoutDirection(Qt.RightToLeft);self.setStyleSheet(APP_STYLE);self.results=[];root=QVBoxLayout(self);top=QHBoxLayout();self.setup_back(top);top.addWidget(QLabel('مركز البحث العام'));top.addStretch();root.addLayout(top)
        hero=QFrame();hero.setObjectName('SearchHero');hl=QVBoxLayout(hero);title=QLabel('ابحث في النظام كله');title.setObjectName('PageTitle');hl.addWidget(title);hint=QLabel('اكتب اسمًا أو رقم فاتورة أو باركود أو هاتف أو حساب. النتائج مجمعة في بطاقة واحدة.');hint.setObjectName('Muted');hl.addWidget(hint);row=QHBoxLayout();self.search=QLineEdit();self.search.setObjectName('GlobalSearchBox');self.search.setPlaceholderText('مثال: INV-2026-000006  أو  770…  أو  اسم العميل…');self.search.returnPressed.connect(self.search_now);row.addWidget(self.search,1);go=QPushButton('بحث');go.setMinimumHeight(48);go.clicked.connect(self.search_now);row.addWidget(go);clear=QPushButton('مسح');clear.clicked.connect(self.clear);row.addWidget(clear);hl.addLayout(row);root.addWidget(hero)
        self.table=QTableWidget();self.table.setSelectionBehavior(QAbstractItemView.SelectRows);self.table.setSelectionMode(QAbstractItemView.SingleSelection);self.table.setColumnCount(5);self.table.setHorizontalHeaderLabels(['النوع','الاسم / الرقم','التفاصيل','المصدر','المعرف']);self.table.doubleClicked.connect(lambda *_:self.open_selected());root.addWidget(self.table,1)
        bottom=QHBoxLayout();self.status=QLabel('جاهز للبحث');bottom.addWidget(self.status);bottom.addStretch();openb=QPushButton('فتح النتيجة');openb.clicked.connect(self.open_selected);bottom.addWidget(openb);root.addLayout(bottom)
    def clear(self):self.search.clear();self.table.setRowCount(0);self.status.setText('جاهز للبحث')
    def search_now(self):
        q=self.search.text().strip();self.results=[]
        if len(q)<1:return self.status.setText('اكتب قيمة للبحث.')
        specs=[('المنتجات','products',['name_ar','name','sku','barcode']),('العملاء','customers',['name_ar','name','phone','mobile','email']),('الموردون','suppliers',['name_ar','name','phone','mobile','email']),('المبيعات','sales',['invoice_number','notes']),('فواتير الشراء','purchase_invoices',['invoice_number','notes']),('الحسابات','accounts',['account_code','account_name','name']),('الموظفون','employees',['name_ar','name','employee_no','phone'])]
        with get_session() as s:
            for title,t,fields in specs:
                if not table_exists(s,t):continue
                cs=columns(s,t); usable=[x for x in fields if x in cs]
                if not usable:continue
                where=' OR '.join(f'CAST("{x}" AS TEXT) LIKE :q' for x in usable)
                for row in s.execute(text(f'SELECT * FROM "{t}" WHERE {where} ORDER BY id DESC LIMIT 60'),{'q':f'%{q}%'}).mappings().all():
                    name=first_value(row,'name_ar','name','invoice_number','sku','barcode','account_name','account_code','employee_no',default=row.get('id')); detail=' | '.join(f'{label(k)}: {display_value(v)}' for k,v in row.items() if k in {'phone','mobile','sku','barcode','total_amount','status','account_code'} and v not in (None,''));self.results.append({'title':title,'name':name,'detail':detail,'table':t,'id':row.get('id')})
        self.table.setRowCount(0)
        for x in self.results:
            r=self.table.rowCount();self.table.insertRow(r);vals=[x['title'],str(x['name']),x['detail'],TABLE_TITLES.get(x['table'],x['table']),str(x['id'])]
            for c,v in enumerate(vals):self.table.setItem(r,c,QTableWidgetItem(str(v)))
        self.status.setText(f'تم العثور على {len(self.results)} نتيجة — اضغط مرتين لفتحها.')
    def open_selected(self):
        r=self.table.currentRow();
        if r<0:return
        x=self.results[r]
        if x['table']=='sales':InvoiceViewDialog('sale',x['id'],self).exec()
        elif x['table']=='purchase_invoices':InvoiceViewDialog('purchase',x['id'],self).exec()
        elif x['table']=='products':InventoryWindow(parent=self).show()
        elif x['table'] in {'customers','suppliers'}:PartyProfileDialog('customer' if x['table']=='customers' else 'supplier',x['id'],self).exec()
        else:AccessDataWindow(x['table'],TABLE_TITLES.get(x['table'],x['table']),parent=self).show()


LANGUAGES = [x for x in '''العربية|English|Français|Español|Deutsch|Italiano|Português|Русский|中文|日本語|한국어|Türkçe|فارسی|اردو|हिन्दी|বাংলা|ਪੰਜਾਬੀ|ગુજરાતી|मराठी|தமிழ்|తెలుగు|ಕನ್ನಡ|മലയാളം|සිංහල|नेपाली|ไทย|Tiếng Việt|Bahasa Indonesia|Bahasa Melayu|Filipino|Nederlands|Svenska|Norsk|Dansk|Suomi|Íslenska|Polski|Čeština|Slovenčina|Magyar|Română|Български|Hrvatski|Српски|Slovenščina|Bosanski|Македонски|Shqip|Ελληνικά|Українська|Беларуская|ქართული|Հայերեն|Azərbaycan|Қазақша|O‘zbekcha|Türkmençe|Кыргызча|Монгол|עברית|Yiddish|Kurdî|Pashto|Dari|Amharic|Somali|Swahili|Hausa|Yoruba|Igbo|Zulu|Xhosa|Afrikaans|Sesotho|Setswana|Shona|Kinyarwanda|Kirundi|Malagasy|Tigrinya|Oromo|Wolof|Bambara|Akan|Lingala|Luganda|Chichewa|Maltese|Irish|Welsh|Català|Galego|Basque|Esperanto|Latin|Estonian|Latvian|Lithuanian|Luxembourgish|Faroese|Greenlandic|Kyrgyz|Tajik|Tatar|Bashkir|Chechen|Ossetian|Uyghur|Khmer|Lao|Burmese|Māori|Samoan|Tongan|Fijian|Hawaiian|Quechua|Aymara|Guarani|Inuktitut|Navajo|Cherokee'''.split('|') if x]
COMMON_CURRENCIES = [
('SAR — الريال السعودي — السعودية','SAR'),('YER — الريال اليمني — اليمن','YER'),('USD — الدولار الأمريكي — الولايات المتحدة','USD'),('EUR — اليورو — منطقة اليورو','EUR'),('GBP — الجنيه الإسترليني — المملكة المتحدة','GBP'),('AED — الدرهم الإماراتي — الإمارات','AED'),('QAR — الريال القطري — قطر','QAR'),('KWD — الدينار الكويتي — الكويت','KWD'),('BHD — الدينار البحريني — البحرين','BHD'),('OMR — الريال العماني — عُمان','OMR'),('JOD — الدينار الأردني — الأردن','JOD'),('EGP — الجنيه المصري — مصر','EGP'),('TRY — الليرة التركية — تركيا','TRY'),('CNY — اليوان الصيني — الصين','CNY'),('JPY — الين الياباني — اليابان','JPY'),('INR — الروبية الهندية — الهند','INR'),('PKR — الروبية الباكستانية — باكستان','PKR'),('MAD — الدرهم المغربي — المغرب','MAD'),('DZD — الدينار الجزائري — الجزائر','DZD'),('TND — الدينار التونسي — تونس','TND'),('LYD — الدينار الليبي — ليبيا','LYD'),('SDG — الجنيه السوداني — السودان','SDG'),('IQD — الدينار العراقي — العراق','IQD'),('LBP — الليرة اللبنانية — لبنان','LBP'),('SYP — الليرة السورية — سوريا','SYP'),('KZT — التينغ الكازاخستاني — كازاخستان','KZT'),('RUB — الروبل الروسي — روسيا','RUB'),('CAD — الدولار الكندي — كندا','CAD'),('AUD — الدولار الأسترالي — أستراليا','AUD'),('NZD — الدولار النيوزيلندي — نيوزيلندا','NZD'),('CHF — الفرنك السويسري — سويسرا','CHF'),('SEK — الكرونة السويدية — السويد','SEK'),('NOK — الكرونة النرويجية — النرويج','NOK'),('DKK — الكرونة الدنماركية — الدنمارك','DKK'),('ZAR — الراند الجنوب أفريقي — جنوب أفريقيا','ZAR'),('BRL — الريال البرازيلي — البرازيل','BRL'),('MXN — البيزو المكسيكي — المكسيك','MXN'),('IDR — الروبية الإندونيسية — إندونيسيا','IDR'),('MYR — الرينغيت الماليزي — ماليزيا','MYR'),('THB — البات التايلندي — تايلاند','THB'),('VND — الدونغ الفيتنامي — فيتنام','VND'),('KRW — الوون الكوري — كوريا الجنوبية','KRW'),('SGD — الدولار السنغافوري — سنغافورة','SGD'),('HKD — دولار هونغ كونغ — هونغ كونغ','HKD'),('PHP — البيزو الفلبيني — الفلبين','PHP'),('NGN — النايرا النيجيرية — نيجيريا','NGN'),('KES — الشلن الكيني — كينيا','KES'),('GHS — السيدي الغاني — غانا','GHS'),('ETB — البِر الإثيوبي — إثيوبيا','ETB'),('MAD — الدرهم المغربي — المغرب','MAD')]


class SettingsWindow(QWidget, BackMixin):
    def __init__(self,user=None,parent=None):
        super().__init__(parent);self.user=user or {};self.setWindowTitle('الإعدادات');self.setMinimumSize(1280,780);self.setLayoutDirection(Qt.RightToLeft);self.setStyleSheet(APP_STYLE);root=QHBoxLayout(self);nav=QFrame();nav.setObjectName('SettingsNav');nl=QVBoxLayout(nav);top=QHBoxLayout();self.setup_back(top);nl.addLayout(top);self.list=QListWidget();items=['المنشأة','النظام واللغة','العملة','التاريخ والوقت','الطباعة','الفاتورة والشعار','الأمان'];self.list.addItems(items);nl.addWidget(self.list,1);root.addWidget(nav,0);self.stack=QStackedWidget();root.addWidget(self.stack,1);self._pages=[];self._build_pages();self.list.currentRowChanged.connect(self.stack.setCurrentIndex);self.list.setCurrentRow(0)
    def _setting_get(self,key,default=''):
        with get_session() as s:
            if not table_exists(s,'system_settings'):return default
            cs=columns(s,'system_settings');k='key' if 'key' in cs else ('setting_key' if 'setting_key' in cs else None);v='value' if 'value' in cs else ('setting_value' if 'setting_value' in cs else None)
            if not k or not v:return default
            x=s.execute(text(f'SELECT "{v}" FROM system_settings WHERE "{k}"=:k LIMIT 1'),{'k':key}).scalar();return default if x is None else str(x)
    def _setting_set(self,key,value):
        with get_session() as s:
            if not table_exists(s,'system_settings'):return
            cs=columns(s,'system_settings');k='key' if 'key' in cs else ('setting_key' if 'setting_key' in cs else None);v='value' if 'value' in cs else ('setting_value' if 'setting_value' in cs else None)
            if not k or not v:return
            old=s.execute(text(f'SELECT id FROM system_settings WHERE "{k}"=:k LIMIT 1'),{'k':key}).scalar()
            if old:s.execute(text(f'UPDATE system_settings SET "{v}"=:v WHERE id=:id'),{'v':value,'id':old})
            else:
                cols2=columns(s,'system_settings'); fields=[k,v]; vals={k:key,v:value}; optional=[x for x in ('value_type','description','is_active') if x in cols2];
                for x in optional:
                    fields.append(x);vals[x]='text' if x=='value_type' else (1 if x=='is_active' else None)
                s.execute(text(f'INSERT INTO system_settings ({",".join(chr(34)+x+chr(34) for x in fields)}) VALUES ({",".join(":"+x for x in fields)})'),vals)
            s.commit()
    def page(self,title):
        p=QWidget();l=QVBoxLayout(p);h=QLabel(title);h.setObjectName('PageTitle');l.addWidget(h);return p,l
    def field(self,l,name,w):l.addRow(name,w);return w
    def _build_pages(self):
        p,l=self.page('بيانات المنشأة');self.company=QLineEdit(self._setting_get('company_name','قرطاسية لؤلؤة الأربعين النموذجية'));self.address=QLineEdit(self._setting_get('company_address',''));self._add_save(l,[('اسم المنشأة',self.company,'company_name'),('العنوان',self.address,'company_address')]);self.stack.addWidget(p)
        p,l=self.page('النظام واللغة والاتجاه');lang=SearchableCombo([(x,x) for x in LANGUAGES]);lang.setCurrentText(self._setting_get('language','العربية'));direction=SearchableCombo([('يمين إلى يسار — RTL','rtl'),('يسار إلى يمين — LTR','ltr'),('تلقائي حسب اللغة','auto')]);direction.setCurrentText(self._setting_get('ui_direction','rtl'));self._add_save(l,[('اللغة — ابحث باسم اللغة',lang,'language'),('اتجاه الواجهة — معالج بحث',direction,'ui_direction')]);self.stack.addWidget(p)
        p,l=self.page('العملة');cur=SearchableCombo(COMMON_CURRENCIES);cur.setCurrentIndex(max(0,cur.findData(self._setting_get('currency_code','SAR'))));self._add_save(l,[('العملة — ابحث بالاختصار أو الاسم أو الدولة',cur,'currency_code')]);self.stack.addWidget(p)
        p,l=self.page('تنسيق التاريخ والوقت');date=SearchableCombo([(x,x) for x in ['dd/MM/yyyy','MM/dd/yyyy','yyyy/MM/dd','yyyy-MM-dd','dd-MM-yyyy','dd.MM.yyyy']]);date.setCurrentText(self._setting_get('date_format','dd/MM/yyyy'));time=SearchableCombo([(x,x) for x in ['HH:mm','HH:mm:ss','hh:mm AP','hh:mm:ss AP']]);time.setCurrentText(self._setting_get('time_format','HH:mm'));self._add_save(l,[('تنسيق التاريخ',date,'date_format'),('تنسيق الوقت',time,'time_format')]);self.stack.addWidget(p)
        p,l=self.page('الطباعة والطابعات');printers=[(p.printerName(),p.printerName()) for p in QPrinterInfo.availablePrinters()];printers=[('طابعة النظام الافتراضية','default')]+printers;printer=SearchableCombo(printers);printer.setCurrentText(self._setting_get('printer_name','default'));paper=SearchableCombo([(x,x) for x in ['A4','A5','A6','Letter','Legal','Executive','B5','80mm رول حراري','58mm رول حراري']]);paper.setCurrentText(self._setting_get('paper_size','A4'));self._add_save(l,[('الطابعة — بحث في الطابعات المتاحة',printer,'printer_name'),('مقاس الورق — معالج بحث',paper,'paper_size')]);self.stack.addWidget(p)
        p,l=self.page('قالب الفاتورة والشعار');template=SearchableCombo([(x,x) for x in ['فاتورة تجارية كاملة','فاتورة سوبرماركت حرارية 80mm','فاتورة حرارية 58mm','فاتورة A4 رسمية','فاتورة ضريبية A4']]);template.setCurrentText(self._setting_get('invoice_template','فاتورة تجارية كاملة'));logo=QLineEdit(self._setting_get('logo_path',''));lb=QPushButton('اختيار ملف الشعار…');lb.clicked.connect(lambda:self.pick_logo(logo));row=QHBoxLayout();row.addWidget(logo,1);row.addWidget(lb);l.addRow('مسار الشعار — اختيار ملف',row);self._add_save(l,[('قالب الفاتورة — معالج بحث',template,'invoice_template')]);self.stack.addWidget(p)
        p,l=self.page('الأمان');info=QLabel('الصلاحيات لا تمنعك من التنقل حاليًا وفق إعداد المشروع. سيتم الاحتفاظ بسجل التدقيق والعمليات المحاسبية.');info.setWordWrap(True);l.addWidget(info);self.stack.addWidget(p)
    def _add_save(self,l,items):
        for caption,w,key in items:l.addRow(caption,w)
        b=QPushButton('حفظ إعدادات هذه الصفحة');b.setMinimumHeight(44);b.clicked.connect(lambda _,items=items:self.save_page(items));l.addRow(b)
    def save_page(self,items):
        for _,w,key in items:self._setting_set(key,w.currentData() if isinstance(w,SearchableCombo) else w.text())
        QMessageBox.information(self,'تم الحفظ','تم حفظ الإعدادات بنجاح. بعض إعدادات الواجهة تُطبق بعد إعادة فتح النظام.')
    def pick_logo(self,w):
        path,_=QFileDialog.getOpenFileName(self,'اختيار شعار','', 'Images (*.png *.jpg *.jpeg *.webp)')
        if path:w.setText(path)


class DashboardWindow(QWidget, BackMixin):
    def __init__(self,main_window=None,parent=None):
        super().__init__(parent);self.main_window=main_window;self.setWindowTitle('لوحة التحكم');self.setMinimumSize(1250,760);self.setLayoutDirection(Qt.RightToLeft);self.setStyleSheet(APP_STYLE);self.build()
    def build(self):
        root=QVBoxLayout(self);top=QHBoxLayout();self.setup_back(top);top.addWidget(QLabel('لوحة التحكم'));top.addStretch();root.addLayout(top);grid=QGridLayout();grid.setSpacing(14);root.addLayout(grid)
        cards=[('مبيعات اليوم','sales'),('مشتريات اليوم','purchases'),('صافي المبيعات','net'),('العملاء','customers'),('الأصناف','products'),('أصناف منخفضة المخزون','low'),('المرتجع اليوم','returns'),('صندوق النقد','cash')]
        self.card_labels={}
        for i,(title,key) in enumerate(cards):
            f=QFrame();f.setObjectName('DashboardCard');v=QVBoxLayout(f);v.addWidget(QLabel(title));num=QLabel('—');num.setObjectName('DashboardNumber');v.addWidget(num);self.card_labels[key]=num;grid.addWidget(f,i//4,i%4)
        body=QHBoxLayout();root.addLayout(body,1);self.alerts=QTableWidget(0,3);self.alerts.setHorizontalHeaderLabels(['التنبيه','العدد','الإجراء']);body.addWidget(self.alerts,1);self.best=QTableWidget(0,3);self.best.setHorizontalHeaderLabels(['الأفضل مبيعًا','الكمية','القيمة']);body.addWidget(self.best,1);self.load_data()
    def load_data(self):
        try:
            with get_session() as s:
                today="date('now','localtime')"; sales=float(s.execute(text(f"SELECT COALESCE(SUM(total_amount),0) FROM sales WHERE date(created_at)={today} AND COALESCE(status,'') NOT IN ('CANCELLED','ملغي')")).scalar() or 0) if table_exists(s,'sales') else 0
                purchases=float(s.execute(text(f"SELECT COALESCE(SUM(total_amount),0) FROM purchase_invoices WHERE date(created_at)={today}")).scalar() or 0) if table_exists(s,'purchase_invoices') else 0
                customers=int(s.execute(text('SELECT COUNT(*) FROM customers')).scalar() or 0) if table_exists(s,'customers') else 0; products=int(s.execute(text('SELECT COUNT(*) FROM products')).scalar() or 0) if table_exists(s,'products') else 0
                low=int(s.execute(text("SELECT COUNT(*) FROM products WHERE COALESCE(min_stock,0)>0 AND COALESCE(quantity,0)<=COALESCE(min_stock,0)")).scalar() or 0) if table_exists(s,'products') and 'min_stock' in columns(s,'products') and 'quantity' in columns(s,'products') else 0
            self.card_labels['sales'].setText(f'{sales:,.2f}');self.card_labels['purchases'].setText(f'{purchases:,.2f}');self.card_labels['net'].setText(f'{sales-purchases:,.2f}');self.card_labels['customers'].setText(f'{customers:,}');self.card_labels['products'].setText(f'{products:,}');self.card_labels['low'].setText(f'{low:,}');self.card_labels['returns'].setText('—');self.card_labels['cash'].setText('—')
        except Exception as exc: self.card_labels['sales'].setText('تعذر القراءة')
