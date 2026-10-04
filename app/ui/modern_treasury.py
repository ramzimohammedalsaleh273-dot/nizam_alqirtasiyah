from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QPushButton,QLabel,QTableWidget,QTableWidgetItem,QAbstractItemView,QDialog,QDialogButtonBox,QDoubleSpinBox,QTextEdit,QMessageBox
from sqlalchemy import text
from app.database.connection import get_session
from app.services.treasury_operations_service import TreasuryOperationsService
from app.services.accounting_service import AccountingService
from app.services.document_number_service import DocumentNumberService
from app.services.audit_service import AuditService
from app.ui.modern_ui import SearchableCombo,BackMixin,table_exists,columns,display_value,human_error
from app.ui.theme import APP_STYLE


def treasury_accounts():
    with get_session() as s:
        TreasuryOperationsService.ensure_schema(s)
        return [(f'{r[1]} — {r[2]}',r[0]) for r in s.execute(text("SELECT id,code,name_ar FROM treasury_accounts WHERE is_active=1 ORDER BY id")).all()]

def gl_accounts():
    with get_session() as s:
        if not table_exists(s,'accounts'):return []
        cs=columns(s,'accounts');name=next((x for x in ('account_name','name_ar','name') if x in cs),'account_code');code='account_code' if 'account_code' in cs else 'id'
        return [(f'{r[1]} — {r[2]}',r[0]) for r in s.execute(text(f'SELECT id,"{code}","{name}" FROM accounts WHERE COALESCE(is_active,1)=1 ORDER BY "{code}" LIMIT 3000')).all()]

class TreasuryVoucherDialog(QDialog):
    def __init__(self,kind,parent=None):
        super().__init__(parent);self.kind=kind;self.setWindowTitle('سند '+kind);self.setMinimumSize(700,540);self.setLayoutDirection(Qt.RightToLeft);self.setStyleSheet(APP_STYLE);root=QVBoxLayout(self);t=QLabel('إنشاء سند '+kind);t.setObjectName('PageTitle');root.addWidget(t);form=QFormLayout();self.treasury=SearchableCombo(treasury_accounts());self.related=SearchableCombo(gl_accounts());self.amount=QDoubleSpinBox();self.amount.setRange(.01,999999999999);self.amount.setDecimals(2);self.reference=QTextEdit();self.reference.setMaximumHeight(70);self.notes=QTextEdit();self.notes.setMaximumHeight(100);form.addRow('حساب الخزينة *',self.treasury);form.addRow('الحساب المقابل *',self.related);form.addRow('المبلغ *',self.amount);form.addRow('المرجع',self.reference);form.addRow('البيان',self.notes);root.addLayout(form);hint=QLabel('قبض: مدين الخزينة / دائن الحساب المقابل. صرف: مدين الحساب المقابل / دائن الخزينة.');hint.setObjectName('Muted');hint.setWordWrap(True);root.addWidget(hint);bb=QDialogButtonBox();bb.addButton('حفظ وترحيل',QDialogButtonBox.AcceptRole);bb.addButton('إلغاء',QDialogButtonBox.RejectRole);bb.accepted.connect(self.accept);bb.rejected.connect(self.reject);root.addWidget(bb)
    def values(self):return {'treasury_account_id':self.treasury.currentData(),'related_account_id':self.related.currentData(),'amount':self.amount.value(),'reference':self.reference.toPlainText().strip() or None,'notes':self.notes.toPlainText().strip() or None}

class TreasuryOperationsWindow(QWidget,BackMixin):
    def __init__(self,user=None,parent=None):
        super().__init__(parent);self.user=user or {};self.setWindowTitle('الخزينة');self.setMinimumSize(1250,760);self.setLayoutDirection(Qt.RightToLeft);self.setStyleSheet(APP_STYLE);root=QVBoxLayout(self);top=QHBoxLayout();self.setup_back(top);top.addWidget(QLabel('الخزينة وحركة النقد'));top.addStretch();root.addLayout(top);actions=QHBoxLayout();r=QPushButton('＋ سند قبض');p=QPushButton('− سند صرف');r.setMinimumHeight(50);p.setMinimumHeight(50);r.clicked.connect(lambda:self.voucher('قبض'));p.clicked.connect(lambda:self.voucher('صرف'));actions.addWidget(r);actions.addWidget(p);actions.addStretch();root.addLayout(actions);self.table=QTableWidget();root.addWidget(self.table,1);self.load()
    def load(self):
        try:
            with get_session() as s:
                TreasuryOperationsService.ensure_schema(s);cs=columns(s,'treasury_movements');rows=s.execute(text('SELECT * FROM treasury_movements ORDER BY id DESC LIMIT 500')).mappings().all()
            self.table.setColumnCount(len(cs));self.table.setHorizontalHeaderLabels([{'document_number':'رقم المستند','treasury_account_id':'حساب الخزينة','movement_type':'نوع الحركة','amount':'المبلغ','reference_number':'المرجع','notes':'البيان','status':'الحالة','created_at':'التاريخ'}.get(x,x.replace('_',' ')) for x in cs]);self.table.setRowCount(0)
            for row in rows:
                r=self.table.rowCount();self.table.insertRow(r)
                for c,k in enumerate(cs):self.table.setItem(r,c,QTableWidgetItem(display_value(row[k])))
        except Exception as exc:QMessageBox.critical(self,'تعذر تحميل الخزينة',human_error(exc))
    def voucher(self,kind):
        d=TreasuryVoucherDialog(kind,self)
        if d.exec()!=QDialog.Accepted:return
        v=d.values()
        if not v['treasury_account_id'] or not v['related_account_id']:return QMessageBox.warning(self,'بيانات ناقصة','اختر حساب الخزينة والحساب المقابل.')
        try:
            with get_session() as s:
                TreasuryOperationsService.ensure_schema(s);ta=s.execute(text('SELECT * FROM treasury_accounts WHERE id=:id'),{'id':v['treasury_account_id']}).mappings().first()
                if not ta:raise ValueError('حساب الخزينة غير موجود.')
                gl=s.execute(text('SELECT id,account_code FROM accounts WHERE id=:id'),{'id':v['related_account_id']}).mappings().first()
                if not gl:raise ValueError('الحساب المقابل غير موجود.')
                cash_id=AccountingService.get_account_id(s,ta['gl_account_code']);counter_id=int(gl['id']);number=DocumentNumberService.next_number(s,'TREASURY_MOVEMENT','RCV' if kind=='قبض' else 'PAY',width=6);entry_no=AccountingService.next_entry_number(s)
                s.execute(text("INSERT INTO journal_entries (entry_number,entry_date,description,source_type,status,created_by,created_at) VALUES (:n,CURRENT_DATE,:d,'TREASURY_VOUCHER','POSTED',:u,CURRENT_TIMESTAMP)"),{'n':entry_no,'d':f'سند {kind} {number}','u':self.user.get('id') or self.user.get('user_id')})
                eid=int(s.execute(text('SELECT last_insert_rowid()')).scalar())
                debit,credit=(cash_id,counter_id) if kind=='قبض' else (counter_id,cash_id)
                s.execute(text("INSERT INTO journal_entry_lines (journal_entry_id,account_id,cost_center_id,description,debit,credit) VALUES (:e,:a,NULL,:d,:de,0)"),{'e':eid,'a':debit,'d':f'سند {kind} {number}','de':v['amount']})
                s.execute(text("INSERT INTO journal_entry_lines (journal_entry_id,account_id,cost_center_id,description,debit,credit) VALUES (:e,:a,NULL,:d,0,:cr)"),{'e':eid,'a':credit,'d':f'سند {kind} {number}','cr':v['amount']})
                s.execute(text("INSERT INTO treasury_movements (document_number,treasury_account_id,movement_type,amount,reference_number,user_id,journal_entry_id,status,notes) VALUES (:n,:a,:t,:amt,:ref,:u,:j,'POSTED',:notes)"),{'n':number,'a':v['treasury_account_id'],'t':'RECEIPT' if kind=='قبض' else 'PAYMENT','amt':v['amount'],'ref':v['reference'],'u':self.user.get('id') or self.user.get('user_id'),'j':eid,'notes':v['notes']})
                AuditService.log(s,'TREASURY_VOUCHER','treasury_movement',number,username=str(self.user.get('id') or 'system'));s.commit()
            self.load();QMessageBox.information(self,'تم الترحيل',f'تم حفظ وترحيل سند {kind} برقم {number}.')
        except Exception as exc:QMessageBox.critical(self,'فشل حفظ سند '+kind,human_error(exc))

VoucherDialog=TreasuryVoucherDialog
