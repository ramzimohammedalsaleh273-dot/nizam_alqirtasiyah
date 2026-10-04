from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QPushButton,QLabel,QTableWidget,QTableWidgetItem,QAbstractItemView,QDialog,QDialogButtonBox,QDoubleSpinBox,QSpinBox,QMessageBox
from sqlalchemy import text
from app.database.connection import get_session
from app.services.purchase_workflow_service import PurchaseWorkflowService
from app.services.permission_service import PermissionService
from app.ui.modern_ui import SearchableCombo, BackMixin, table_exists, columns, display_value, human_error
from app.ui.theme import APP_STYLE


def lookup_items(table, names=('name_ar','name','code','sku')):
    with get_session() as s:
        if not table_exists(s, table): return []
        cs=columns(s,table); display=next((x for x in names if x in cs),'id')
        return [(f'{r[1]}  |  #{r[0]}',r[0]) for r in s.execute(text(f'SELECT id,"{display}" FROM {table} ORDER BY id LIMIT 5000')).all()]


class WorkflowItemDialog(QDialog):
    def __init__(self, mode, parent=None):
        super().__init__(parent);self.mode=mode;self.setWindowTitle('طلب شراء جديد' if mode=='request' else 'إنشاء أمر شراء');self.setMinimumSize(650,480);self.setLayoutDirection(Qt.RightToLeft);self.setStyleSheet(APP_STYLE);root=QVBoxLayout(self);title=QLabel(self.windowTitle());title.setObjectName('PageTitle');root.addWidget(title);form=QFormLayout();self.product=SearchableCombo(lookup_items('products',('name_ar','name','sku','barcode')));self.qty=QDoubleSpinBox();self.qty.setRange(.001,999999999);self.qty.setDecimals(3);self.qty.setValue(1);form.addRow('الصنف *',self.product);form.addRow('الكمية *',self.qty)
        if mode=='order':
            self.supplier=SearchableCombo(lookup_items('suppliers'));self.cost=QDoubleSpinBox();self.cost.setRange(0,999999999);self.cost.setDecimals(2);form.addRow('المورد *',self.supplier);form.addRow('تكلفة الوحدة',self.cost)
        root.addLayout(form);bb=QDialogButtonBox();bb.addButton('حفظ',QDialogButtonBox.AcceptRole);bb.addButton('إلغاء',QDialogButtonBox.RejectRole);bb.accepted.connect(self.accept);bb.rejected.connect(self.reject);root.addWidget(bb)
    def values(self):
        return {'product_id':self.product.currentData(),'quantity':self.qty.value(),'supplier_id':self.supplier.currentData() if self.mode=='order' else None,'unit_cost':self.cost.value() if self.mode=='order' else None}


class PurchaseWorkflowWindow(QWidget, BackMixin):
    def __init__(self,user=None,parent=None):
        super().__init__(parent);self.user=dict(user or {});self.setWindowTitle('دورة المشتريات');self.setMinimumSize(1250,760);self.setLayoutDirection(Qt.RightToLeft);self.setStyleSheet(APP_STYLE);root=QVBoxLayout(self);top=QHBoxLayout();self.setup_back(top);top.addWidget(QLabel('دورة المشتريات'));top.addStretch();root.addLayout(top);hint=QLabel('المسار التشغيلي: طلب شراء ← اعتماد ← أمر شراء ← استلام ← فاتورة شراء.');hint.setObjectName('Muted');root.addWidget(hint);actions=QHBoxLayout();
        for cap,fn in [('＋ طلب شراء جديد',self.new_request),('✓ اعتماد الطلب',self.approve),('＋ إنشاء أمر شراء',self.new_order),('استلام أمر الشراء',self.receive),('↻ تحديث',self.load)]:b=QPushButton(cap);b.setMinimumHeight(44);b.clicked.connect(fn);actions.addWidget(b)
        actions.addStretch();root.addLayout(actions);self.table=QTableWidget();self.table.setSelectionBehavior(QAbstractItemView.SelectRows);self.table.setSelectionMode(QAbstractItemView.SingleSelection);self.table.setColumnCount(5);self.table.setHorizontalHeaderLabels(['المعرف','النوع','الرقم','الحالة','التاريخ']);root.addWidget(self.table,1);self.status=QLabel('');root.addWidget(self.status);self.load()
    def uid(self):
        uid=self.user.get('id') or self.user.get('user_id') or PermissionService.default_user_id()
        if uid is None: raise ValueError('لا يوجد مستخدم فعّال لتنفيذ العملية.')
        return int(uid)
    def load(self):
        try:
            with get_session() as s:
                PurchaseWorkflowService.ensure_schema(s)
                req=s.execute(text('SELECT id,\'طلب شراء\' kind,request_number number,status,created_at FROM purchase_requests ORDER BY id DESC LIMIT 200')).all() if table_exists(s,'purchase_requests') else []
                orders=s.execute(text('SELECT id,\'أمر شراء\' kind,order_number number,status,created_at FROM purchase_orders ORDER BY id DESC LIMIT 200')).all() if table_exists(s,'purchase_orders') else []
            self.table.setRowCount(0)
            for row in list(req)+list(orders):
                r=self.table.rowCount();self.table.insertRow(r)
                for c,v in enumerate(row):self.table.setItem(r,c,QTableWidgetItem(display_value(v)))
            self.status.setText(f'المستندات المعروضة: {self.table.rowCount():,}')
        except Exception as exc:QMessageBox.critical(self,'تعذر تحميل دورة المشتريات',human_error(exc))
    def selected(self):
        r=self.table.currentRow()
        if r<0:return None
        return [self.table.item(r,c).text() if self.table.item(r,c) else '' for c in range(5)]
    def new_request(self):
        d=WorkflowItemDialog('request',self)
        if d.exec()!=QDialog.Accepted:return
        v=d.values()
        if not v['product_id']:return QMessageBox.warning(self,'طلب الشراء','اختر الصنف.')
        try:PurchaseWorkflowService.create_request([{'product_id':v['product_id'],'quantity':v['quantity']}],requester_id=self.uid());self.load();QMessageBox.information(self,'تم','تم إنشاء طلب الشراء وحفظه فعليًا.')
        except Exception as exc:QMessageBox.critical(self,'فشل إنشاء الطلب',human_error(exc))
    def approve(self):
        row=self.selected()
        if not row:return QMessageBox.information(self,'اعتماد الطلب','حدد طلب شراء.')
        if row[1]!='طلب شراء':return QMessageBox.warning(self,'اعتماد الطلب','حدد طلب شراء وليس أمر شراء.')
        try:PurchaseWorkflowService.approve_request(int(row[0]),self.uid());self.load()
        except Exception as exc:QMessageBox.critical(self,'فشل الاعتماد',human_error(exc))
    def new_order(self):
        row=self.selected()
        if not row or row[1]!='طلب شراء':return QMessageBox.warning(self,'أمر الشراء','حدد طلب شراء.')
        d=WorkflowItemDialog('order',self)
        if d.exec()!=QDialog.Accepted:return
        v=d.values()
        if not v['supplier_id'] or not v['product_id']:return QMessageBox.warning(self,'أمر الشراء','اختر المورد والصنف.')
        try:PurchaseWorkflowService.create_purchase_order(int(row[0]),int(v['supplier_id']),[{'product_id':int(v['product_id']),'quantity':v['quantity'],'unit_cost':v['unit_cost']}]);self.load();QMessageBox.information(self,'تم','تم إنشاء أمر الشراء.')
        except Exception as exc:QMessageBox.critical(self,'فشل إنشاء أمر الشراء',human_error(exc))
    def receive(self):
        row=self.selected()
        if not row or row[1]!='أمر شراء':return QMessageBox.warning(self,'الاستلام','حدد أمر شراء.')
        try:
            result=PurchaseWorkflowService.receive_order(int(row[0]),user_id=self.uid());self.load();inv=(result.get('purchase_invoice') or {}).get('invoice_number','—');QMessageBox.information(self,'تم الاستلام',f'تم الاستلام وإنشاء فاتورة شراء {inv}.')
        except Exception as exc:QMessageBox.critical(self,'فشل الاستلام',human_error(exc))
