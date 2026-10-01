from app.ui.theme import APP_STYLE
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QTableWidget,QTableWidgetItem,QMessageBox,QHeaderView
from app.services.backup_service import BackupService
from app.services.backup_manager_service import BackupManagerService


class BackupWindow(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setStyleSheet(APP_STYLE)
        self.setWindowTitle("النسخ الاحتياطي والاستعادة")
        self.setMinimumSize(950,600)
        layout=QVBoxLayout(self)
        bar=QHBoxLayout()
        create=QPushButton("إنشاء نسخة الآن")
        refresh=QPushButton("تحديث")
        verify=QPushButton("فحص النسخة المحددة")
        restore=QPushButton("استعادة النسخة المحددة")
        create.clicked.connect(self.create_backup)
        refresh.clicked.connect(self.load)
        verify.clicked.connect(self.verify_selected)
        restore.clicked.connect(self.restore_selected)
        for b in (create,refresh,verify,restore): bar.addWidget(b)
        bar.addStretch()
        layout.addLayout(bar)
        self.table=QTableWidget(0,4)
        self.table.setHorizontalHeaderLabels(["الملف","الحجم","سلامة القاعدة","المسار"])
        self.table.horizontalHeader().setSectionResizeMode(3,QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)
        self.load()

    def load(self):
        self.table.setRowCount(0)
        for item in BackupManagerService.list_backups():
            row=self.table.rowCount(); self.table.insertRow(row)
            values=[item["path"].name, f'{item["size"]/1024:.1f} كيلوبايت', "سليمة" if item["valid"] else "غير سليمة", str(item["path"])]
            for col,value in enumerate(values): self.table.setItem(row,col,QTableWidgetItem(value))

    def selected_path(self):
        row=self.table.currentRow()
        if row<0: return None
        return self.table.item(row,3).text()

    def create_backup(self):
        try:
            path=BackupService.create_backup()
            self.load(); QMessageBox.information(self,"النسخ الاحتياطي",f"تم إنشاء نسخة سليمة:\n{path}")
        except Exception as exc: QMessageBox.critical(self,"فشل النسخ",str(exc))

    def verify_selected(self):
        path=self.selected_path()
        if not path: return QMessageBox.warning(self,"تنبيه","اختر نسخة أولاً")
        try:
            BackupManagerService.verify(path); QMessageBox.information(self,"الفحص","النسخة سليمة وقابلة للاستخدام.")
        except Exception as exc: QMessageBox.critical(self,"فشل الفحص",str(exc))

    def restore_selected(self):
        path=self.selected_path()
        if not path: return QMessageBox.warning(self,"تنبيه","اختر نسخة أولاً")
        answer=QMessageBox.question(self,"تأكيد الاستعادة","سيتم إنشاء نسخة أمان من قاعدة البيانات الحالية قبل الاستعادة. هل تريد المتابعة؟")
        if answer != QMessageBox.Yes: return
        try:
            restored,safety=BackupManagerService.restore(path)
            QMessageBox.information(self,"تمت الاستعادة",f"تمت الاستعادة بنجاح.\nالنسخة الأمنية: {safety}\n\nأعد تشغيل البرنامج لتأكيد تحميل القاعدة الجديدة.")
        except Exception as exc: QMessageBox.critical(self,"فشل الاستعادة",str(exc))

# UI reference theme is applied by the main application shell.
