from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLineEdit,QPushButton,QLabel,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QDialog,QFormLayout,QDialogButtonBox,QDoubleSpinBox,QComboBox,QMessageBox
from app.ui.theme import APP_STYLE
from app.services.expense_service import ExpenseService

class ExpenseWindow(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent); self.setStyleSheet(APP_STYLE); self.setWindowTitle("المصروفات"); self.setMinimumSize(1100,680); self.setLayoutDirection(Qt.RightToLeft)
        root=QVBoxLayout(self); h=QHBoxLayout(); t=QLabel("المصروفات"); t.setObjectName("SectionTitle"); h.addWidget(t); h.addStretch()
        add=QPushButton("إضافة مصروف"); add.setObjectName("Success"); add.clicked.connect(self.add); h.addWidget(add); root.addLayout(h)
        bar=QHBoxLayout(); bar.addWidget(QLabel("بحث:")); self.search=QLineEdit(); self.search.setPlaceholderText("بحث في الرقم أو التصنيف أو البيان…"); self.search.textChanged.connect(self.load); bar.addWidget(self.search,1)
        refresh=QPushButton("تحديث"); refresh.clicked.connect(self.load); bar.addWidget(refresh); root.addLayout(bar)
        self.table=QTableWidget(0,8); self.table.setHorizontalHeaderLabels(["الرقم","رقم المصروف","التاريخ","التصنيف","البيان","المبلغ","طريقة الدفع","الحالة"]); self.table.setSelectionBehavior(QAbstractItemView.SelectRows); self.table.setEditTriggers(QAbstractItemView.NoEditTriggers); self.table.setAlternatingRowColors(True); self.table.horizontalHeader().setSectionResizeMode(4,QHeaderView.Stretch); root.addWidget(self.table,1)
        self.status=QLabel("جاهز"); root.addWidget(self.status); self.load()
    def load(self):
        q=self.search.text().strip().lower(); rows=ExpenseService.list_expenses(); rows=[r for r in rows if not q or q in str(r.get("expense_number","")).lower() or q in str(r.get("category","")).lower() or q in str(r.get("description","")).lower()]
        self.table.setRowCount(0)
        for x in rows:
            r=self.table.rowCount(); self.table.insertRow(r)
            vals=[x.get("id"),x.get("expense_number"),x.get("expense_date"),x.get("category"),x.get("description"),f'{float(x.get("amount") or 0):,.2f}',x.get("payment_method"),x.get("status")]
            for c,v in enumerate(vals): self.table.setItem(r,c,QTableWidgetItem("" if v is None else str(v)))
        self.status.setText(f"السجلات: {len(rows):,}")
    def add(self):
        d=QDialog(self); d.setWindowTitle("إضافة مصروف"); d.setLayoutDirection(Qt.RightToLeft); f=QFormLayout(d)
        cat=QLineEdit(); desc=QLineEdit(); amount=QDoubleSpinBox(); amount.setRange(0,999999999); amount.setDecimals(2); method=QComboBox(); method.addItems(["cash","card","bank_transfer"]); acc=QLineEdit(); notes=QLineEdit()
        f.addRow("التصنيف:",cat); f.addRow("البيان:",desc); f.addRow("المبلغ:",amount); f.addRow("طريقة الدفع:",method); f.addRow("حساب المصروف (اختياري):",acc); f.addRow("ملاحظات:",notes)
        b=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); b.accepted.connect(d.accept); b.rejected.connect(d.reject); f.addRow(b)
        if d.exec()!=QDialog.Accepted:return
        try:
            account=int(acc.text()) if acc.text().strip() else None
            r=ExpenseService.create(cat.text().strip(),desc.text().strip(),amount.value(),method.currentText(),account,None,None,notes.text().strip() or None)
            QMessageBox.information(self,"تم",f"تم تسجيل المصروف {r['expense_number']} وإنشاء القيد المحاسبي {r['journal_entry_id']}."); self.load()
        except Exception as e: QMessageBox.critical(self,"فشل تسجيل المصروف",str(e))
