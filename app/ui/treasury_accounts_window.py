from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QLabel,QTabWidget,QMessageBox,QInputDialog
from app.ui.access_data_window import AccessDataWindow
from app.services.treasury_operations_service import TreasuryOperationsService
from app.ui.theme import APP_STYLE

class TreasuryAccountsWindow(QWidget):
    def __init__(self,user=None,parent=None):
        super().__init__(parent);self.user=user or {};self.setWindowTitle('حسابات الخزينة والبنوك');self.setMinimumSize(1250,760);self.setLayoutDirection(Qt.RightToLeft);self.setStyleSheet(APP_STYLE);root=QVBoxLayout(self);h=QHBoxLayout();h.addWidget(QLabel('حسابات الخزينة والبنوك'));h.addStretch();transfer=QPushButton('تحويل بين الحسابات');transfer.clicked.connect(self.transfer);h.addWidget(transfer);refresh=QPushButton('تحديث');refresh.clicked.connect(self.reload);h.addWidget(refresh);root.addLayout(h);self.tabs=QTabWidget();root.addWidget(self.tabs,1);self.tabs.addTab(AccessDataWindow('treasury_accounts','حسابات الخزينة',user=self.user,parent=self),'حسابات الخزينة');self.tabs.addTab(AccessDataWindow('bank_accounts','الحسابات البنكية',user=self.user,parent=self),'الحسابات البنكية');self.tabs.addTab(AccessDataWindow('cash_registers','الصناديق',user=self.user,parent=self),'الصناديق')
    def reload(self):
        for i in range(self.tabs.count()):
            w=self.tabs.widget(i)
            if hasattr(w,'load'):w.load()
    def transfer(self):
        try:rows=TreasuryOperationsService.list_accounts()
        except Exception as e:return QMessageBox.critical(self,'التحويل',str(e))
        if len(rows)<2:return QMessageBox.warning(self,'التحويل','يلزم وجود حسابي خزينة نشطين على الأقل.')
        labels=[f"{x['id']} - {x['name_ar']}" for x in rows];src,ok=QInputDialog.getItem(self,'التحويل','من الحساب:',labels,0,False)
        if not ok:return
        dst,ok=QInputDialog.getItem(self,'التحويل','إلى الحساب:',labels,1,False)
        if not ok:return
        amount,ok=QInputDialog.getDouble(self,'التحويل','المبلغ:',0,0.01,999999999,2)
        if not ok:return
        try:TreasuryOperationsService.transfer(int(src.split(' - ')[0]),int(dst.split(' - ')[0]),amount,int(self.user.get('id') or 1),None);self.reload();QMessageBox.information(self,'تم','تم تنفيذ التحويل وربطه بالحسابات.')
        except Exception as e:QMessageBox.critical(self,'فشل التحويل',str(e))

__all__=['TreasuryAccountsWindow']
