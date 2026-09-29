from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QLabel,QInputDialog,QMessageBox
from app.services.party_payment_service import PartyPaymentService
from app.services.cashier_session_service import CashierSessionService

class TreasuryOperationsWindow(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWindowTitle("الخزينة والبنوك - التشغيل")
        self.setMinimumSize(900,600)
        layout=QVBoxLayout(self)
        title=QLabel("الخزينة والبنوك")
        title.setStyleSheet("font-size:28px;font-weight:bold")
        layout.addWidget(title)
        for label,handler in [
            ("تحصيل من عميل",self.receive_customer),
            ("دفع لمورد",self.pay_supplier),
            ("فتح جلسة كاشير",self.open_cashier),
            ("إغلاق جلسة كاشير",self.close_cashier),
        ]:
            b=QPushButton(label); b.clicked.connect(handler); layout.addWidget(b)
        layout.addStretch()

    def _amount(self,title):
        value,ok=QInputDialog.getDouble(self,title,"المبلغ:",0,0,999999999,2)
        return value if ok else None

    def receive_customer(self):
        cid,ok=QInputDialog.getInt(self,"تحصيل","رقم العميل:",1,1,2147483647)
        if not ok:return
        amount=self._amount("تحصيل من العميل")
        if amount is None:return
        method,ok=QInputDialog.getItem(self,"طريقة التحصيل","الطريقة:",["cash","card","bank_transfer"],0,False)
        if not ok:return
        try:
            r=PartyPaymentService.receive_from_customer(cid,amount,method)
            QMessageBox.information(self,"تم",f"تم التحصيل بنجاح\nالرصيد الجديد: {r['balance']:.2f}")
        except Exception as e: QMessageBox.critical(self,"فشل التحصيل",str(e))

    def pay_supplier(self):
        sid,ok=QInputDialog.getInt(self,"دفع للمورد","رقم المورد:",1,1,2147483647)
        if not ok:return
        amount=self._amount("دفع للمورد")
        if amount is None:return
        method,ok=QInputDialog.getItem(self,"طريقة الدفع","الطريقة:",["cash","card","bank_transfer"],0,False)
        if not ok:return
        try:
            r=PartyPaymentService.pay_supplier(sid,amount,method)
            QMessageBox.information(self,"تم",f"تم الدفع بنجاح\nالرصيد الجديد: {r['balance']:.2f}")
        except Exception as e: QMessageBox.critical(self,"فشل الدفع",str(e))

    def open_cashier(self):
        cid,ok=QInputDialog.getInt(self,"فتح جلسة","رقم الكاشير/المستخدم (0 بدون ربط):",0,0,2147483647)
        if not ok:return
        amount=self._amount("رصيد افتتاح الصندوق")
        if amount is None:return
        try:
            sid=CashierSessionService.open(None if cid==0 else cid,amount)
            QMessageBox.information(self,"تم",f"تم فتح الجلسة رقم {sid}")
        except Exception as e: QMessageBox.critical(self,"فشل فتح الجلسة",str(e))

    def close_cashier(self):
        sid,ok=QInputDialog.getInt(self,"إغلاق جلسة","رقم الجلسة:",1,1,2147483647)
        if not ok:return
        amount=self._amount("النقد الفعلي في الصندوق")
        if amount is None:return
        try:
            r=CashierSessionService.close(sid,amount)
            QMessageBox.information(self,"تم",f"المتوقع: {r['expected']:.2f}\nالفعلي: {r['actual']:.2f}\nالفرق: {r['difference']:.2f}")
        except Exception as e: QMessageBox.critical(self,"فشل الإغلاق",str(e))
