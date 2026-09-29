from PySide6.QtWidgets import QWidget,QVBoxLayout,QPushButton,QTableWidget,QTableWidgetItem,QMessageBox,QLabel
from app.services.system_validation_service import SystemValidationService
from app.services.accounting_reports_service import AccountingReportsService

class EnterpriseToolsWindow(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent);self.setWindowTitle("مركز التشغيل والفحص المتقدم");self.resize(1100,650)
        l=QVBoxLayout(self);l.addWidget(QLabel("مركز التشغيل والفحص المتقدم"))
        for name,fn in [("فحص النظام الكامل",self.health),("ميزان المراجعة",lambda:self.report("ميزان المراجعة",AccountingReportsService.trial_balance())),("قائمة الدخل",lambda:self.report("قائمة الدخل",AccountingReportsService.income_statement())),("الميزانية",lambda:self.report("الميزانية",AccountingReportsService.balance_sheet()))]:
            b=QPushButton(name);b.clicked.connect(fn);l.addWidget(b)
        self.table=QTableWidget();l.addWidget(self.table)
    def health(self):
        r=SystemValidationService.run();self.table.setColumnCount(3);self.table.setHorizontalHeaderLabels(["الفحص","الحالة","التفاصيل"]);self.table.setRowCount(len(r["checks"]))
        for i,x in enumerate(r["checks"]):
            self.table.setItem(i,0,QTableWidgetItem(x["name"]));self.table.setItem(i,1,QTableWidgetItem("ناجح" if x["ok"] else "فشل"));self.table.setItem(i,2,QTableWidgetItem(x["detail"]))
        if not r["healthy"]:QMessageBox.warning(self,"الفحص","توجد عناصر تحتاج معالجة")
    def report(self,title,rows):
        self.table.setRowCount(0);self.table.setColumnCount(0)
        if not rows:return
        keys=list(rows[0].keys());self.table.setColumnCount(len(keys));self.table.setHorizontalHeaderLabels(keys);self.table.setRowCount(len(rows))
        for i,row in enumerate(rows):
            for j,k in enumerate(keys):self.table.setItem(i,j,QTableWidgetItem(str(row.get(k,""))))
