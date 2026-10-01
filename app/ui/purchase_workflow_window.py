from app.ui.theme import APP_STYLE
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QTableWidget,QTableWidgetItem,QPushButton,QMessageBox,QInputDialog,QDoubleSpinBox,QFormLayout,QDialog,QDialogButtonBox,QSpinBox
from sqlalchemy import text
from app.database.connection import get_session
from app.services.purchase_workflow_service import PurchaseWorkflowService
from app.services.permission_service import PermissionService


class PurchaseWorkflowWindow(QWidget):
    """واجهة تشغيلية لدورة طلبات وأوامر الشراء والاستلام."""
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setStyleSheet(APP_STYLE)
        self.setStyleSheet(APP_STYLE)
        self.setWindowTitle("دورة المشتريات")
        self.setMinimumSize(1100,650)
        root=QVBoxLayout(self)
        bar=QHBoxLayout()
        for caption,handler in [
            ("طلب شراء جديد",self.new_request),
            ("اعتماد الطلب",self.approve),
            ("إنشاء أمر شراء",self.new_order),
            ("استلام أمر",self.receive),
            ("تحديث",self.load),
        ]:
            b=QPushButton(caption); b.clicked.connect(handler); bar.addWidget(b)
        bar.addStretch(); root.addLayout(bar)
        self.table=QTableWidget(0,4)
        self.table.setHorizontalHeaderLabels(["المعرف","النوع","الرقم","الحالة"])
        root.addWidget(self.table)
        self.load()

    def load(self):
        with get_session() as s:
            PurchaseWorkflowService.ensure_schema(s)
            req=s.execute(text("SELECT id,'طلب شراء' AS kind,request_number AS number,status FROM purchase_requests ORDER BY id DESC LIMIT 100")).fetchall()
            orders=s.execute(text("SELECT id,'أمر شراء' AS kind,order_number AS number,status FROM purchase_orders ORDER BY id DESC LIMIT 100")).fetchall()
        self.table.setRowCount(0)
        for r in list(req)+list(orders):
            i=self.table.rowCount(); self.table.insertRow(i)
            for j,v in enumerate(r): self.table.setItem(i,j,QTableWidgetItem(str(v)))

    def selected(self):
        row=self.table.currentRow()
        if row<0:
            QMessageBox.warning(self,"تنبيه","اختر مستندًا أولاً"); return None
        return [self.table.item(row,c).text() for c in range(4)]

    def new_request(self):
        product,ok=QInputDialog.getInt(self,"طلب شراء","رقم الصنف:",1,1,999999)
        if not ok:return
        qty,ok=QInputDialog.getDouble(self,"طلب شراء","الكمية:",1,0.01,999999,2)
        if not ok:return
        try:
            PurchaseWorkflowService.create_request([{"product_id":product,"quantity":qty}], requester_id=PermissionService.default_user_id())
            self.load(); QMessageBox.information(self,"تم","تم إنشاء طلب شراء فعلي وحفظه في قاعدة البيانات.")
        except Exception as e: QMessageBox.critical(self,"فشل",str(e))

    def approve(self):
        row=self.selected()
        if not row:return
        if row[1]!="طلب شراء": QMessageBox.warning(self,"تنبيه","اختر طلب شراء."); return
        try:
            PurchaseWorkflowService.approve_request(int(row[0]), PermissionService.default_user_id())
            self.load()
        except Exception as e: QMessageBox.critical(self,"فشل الاعتماد",str(e))

    def new_order(self):
        row=self.selected()
        if not row or row[1]!="طلب شراء": QMessageBox.warning(self,"تنبيه","اختر طلب شراء معتمدًا."); return
        supplier,ok=QInputDialog.getInt(self,"أمر شراء","رقم المورد:",1,1,999999)
        if not ok:return
        product,ok=QInputDialog.getInt(self,"أمر شراء","رقم الصنف:",1,1,999999)
        if not ok:return
        qty,ok=QInputDialog.getDouble(self,"أمر شراء","الكمية:",1,0.01,999999,2)
        if not ok:return
        cost,ok=QInputDialog.getDouble(self,"أمر شراء","تكلفة الوحدة:",0,0,999999999,2)
        if not ok:return
        try:
            PurchaseWorkflowService.create_purchase_order(int(row[0]),supplier,[{"product_id":product,"quantity":qty,"unit_cost":cost}])
            self.load()
        except Exception as e: QMessageBox.critical(self,"فشل الأمر",str(e))

    def receive(self):
        row=self.selected()
        if not row or row[1]!="أمر شراء": QMessageBox.warning(self,"تنبيه","اختر أمر شراء."); return
        try:
            result=PurchaseWorkflowService.receive_order(int(row[0]))
            self.load()
            QMessageBox.information(self,"تم الاستلام",f"تم إنشاء فاتورة شراء {result['purchase_invoice']['invoice_number']}.")
        except Exception as e: QMessageBox.critical(self,"فشل الاستلام",str(e))

# UI reference theme is applied by the main application shell.
