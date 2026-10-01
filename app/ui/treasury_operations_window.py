from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QLabel,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QInputDialog,QMessageBox,QTabWidget
from sqlalchemy import text
from app.database.connection import get_session
from app.services.party_payment_service import PartyPaymentService
from app.services.cashier_session_service import CashierSessionService
from app.services.permission_service import PermissionService
from app.services.treasury_operations_service import TreasuryOperationsService
from app.ui.theme import APP_STYLE

class TreasuryOperationsWindow(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent); self.setStyleSheet(APP_STYLE); self.setWindowTitle("الخزينة"); self.setMinimumSize(1150,700); self.setLayoutDirection(Qt.RightToLeft)
        root=QVBoxLayout(self); h=QHBoxLayout(); t=QLabel("الخزينة والصناديق"); t.setObjectName("SectionTitle"); h.addWidget(t); h.addStretch()
        for cap,fn,obj in [("سند قبض",self.receive_customer,"Success"),("سند صرف",self.pay_supplier,"Danger"),("فتح وردية",self.open_cashier,"Primary"),("إغلاق وردية",self.close_cashier,"Warning"),("تحديث",self.load,"Secondary")]:
            b=QPushButton(cap); b.setObjectName(obj); b.clicked.connect(fn); h.addWidget(b)
        root.addLayout(h)
        self.tabs=QTabWidget(); root.addWidget(self.tabs,1)
        self.tables={}
        for key,caption,table,cols in [
            ("receipts","سندات القبض","cash_receipts",["id","receipt_number","receipt_date","customer_id","amount","payment_method","reference_number","notes"]),
            ("payments","سندات الصرف","cash_payments",["id","payment_number","payment_date","supplier_id","amount","payment_method","reference_number","notes"]),
            ("sessions","الورديات","cash_sessions",["id","register_id","user_id","opened_at","opening_balance","expected_balance","actual_balance","difference","closed_at","status"]),
            ("movements","حركات الخزينة","cash_transactions",["id","transaction_type","amount","reference_type","reference_id","notes","created_at"])
        ]:
            w=QTableWidget(0,len(cols)); w.setHorizontalHeaderLabels(cols); w.setSelectionBehavior(QAbstractItemView.SelectRows); w.setEditTriggers(QAbstractItemView.NoEditTriggers); w.setAlternatingRowColors(True); w.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents); self.tabs.addTab(w,caption); self.tables[key]=(w,table,cols)
        self.status=QLabel("جاهز"); root.addWidget(self.status); self.load()
    def _user(self):
        uid=PermissionService.default_user_id()
        if uid is None: raise ValueError("لا يوجد مستخدم فعال")
        return uid
    def load(self):
        with get_session() as s:
            for _,(w,table,cols) in self.tables.items():
                exists=s.execute(text("SELECT 1 FROM sqlite_master WHERE type IN ('table','view') AND name=:n"),{"n":table}).scalar()
                w.setRowCount(0)
                if not exists: continue
                rows=s.execute(text(f'SELECT {",".join(chr(34)+c+chr(34) for c in cols)} FROM "{table}" ORDER BY rowid DESC LIMIT 200')).all()
                for row in rows:
                    r=w.rowCount(); w.insertRow(r)
                    for c,v in enumerate(row): w.setItem(r,c,QTableWidgetItem("" if v is None else str(v)))
        self.status.setText("تم تحديث الخزينة والورديات.")
    def _amount(self,title):
        v,ok=QInputDialog.getDouble(self,title,"المبلغ:",0,0,999999999,2); return v if ok else None
    def receive_customer(self):
        cid,ok=QInputDialog.getInt(self,"سند قبض","رقم العميل:",1,1,2147483647)
        if not ok:return
        amount=self._amount("قبض من العميل")
        if amount is None:return
        method,ok=QInputDialog.getItem(self,"طريقة القبض","الطريقة:",["cash","card","bank_transfer"],0,False)
        if not ok:return
        try: PartyPaymentService.receive_from_customer(cid,amount,method,cashier_id=self._user()); self.load(); QMessageBox.information(self,"تم","تم تسجيل سند القبض وربطه بالذمم والخزينة.")
        except Exception as e: QMessageBox.critical(self,"فشل القبض",str(e))
    def pay_supplier(self):
        sid,ok=QInputDialog.getInt(self,"سند صرف","رقم المورد:",1,1,2147483647)
        if not ok:return
        amount=self._amount("دفع للمورد")
        if amount is None:return
        method,ok=QInputDialog.getItem(self,"طريقة الدفع","الطريقة:",["cash","card","bank_transfer"],0,False)
        if not ok:return
        try: PartyPaymentService.pay_supplier(sid,amount,method,cashier_id=self._user()); self.load(); QMessageBox.information(self,"تم","تم تسجيل سند الصرف وربطه بالذمم والخزينة.")
        except Exception as e: QMessageBox.critical(self,"فشل الصرف",str(e))
    def open_cashier(self):
        amount=self._amount("الرصيد الافتتاحي للوردية")
        if amount is None:return
        try: sid=CashierSessionService.open(None,amount,opened_by=self._user()); self.load(); QMessageBox.information(self,"تم",f"تم فتح الوردية رقم {sid}.")
        except Exception as e: QMessageBox.critical(self,"فشل فتح الوردية",str(e))
    def close_cashier(self):
        sid,ok=QInputDialog.getInt(self,"إغلاق وردية","رقم الوردية:",1,1,2147483647)
        if not ok:return
        amount=self._amount("النقد الفعلي")
        if amount is None:return
        try: r=CashierSessionService.close(sid,amount,closed_by=self._user()); self.load(); QMessageBox.information(self,"تقرير الإغلاق",f"المتوقع: {r['expected']:.2f}\nالفعلي: {r['actual']:.2f}\nالفرق: {r['difference']:.2f}")
        except Exception as e: QMessageBox.critical(self,"فشل الإغلاق",str(e))
