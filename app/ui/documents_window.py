from PySide6.QtCore import Qt,QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLineEdit,QPushButton,QLabel,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QFileDialog,QDialog,QFormLayout,QDialogButtonBox,QMessageBox
from sqlalchemy import text
from app.database.connection import get_session
from app.ui.theme import APP_STYLE

class DocumentsWindow(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent); self.setStyleSheet(APP_STYLE); self.setWindowTitle("المستندات والمرفقات"); self.setMinimumSize(1150,700); self.setLayoutDirection(Qt.RightToLeft)
        root=QVBoxLayout(self); h=QHBoxLayout(); t=QLabel("المستندات والمرفقات"); t.setObjectName("SectionTitle"); h.addWidget(t); h.addStretch(); a=QPushButton("إضافة مستند"); a.setObjectName("Success"); a.clicked.connect(self.add); h.addWidget(a); root.addLayout(h)
        bar=QHBoxLayout(); bar.addWidget(QLabel("بحث:")); self.search=QLineEdit(); self.search.setPlaceholderText("رقم المستند أو العنوان أو اسم الملف…"); self.search.textChanged.connect(self.load); bar.addWidget(self.search,1); root.addLayout(bar)
        self.table=QTableWidget(0,7); self.table.setHorizontalHeaderLabels(["المعرف","رقم المستند","العنوان","النوع","الكيان","اسم الملف","المسار"]); self.table.setSelectionBehavior(QAbstractItemView.SelectRows); self.table.setEditTriggers(QAbstractItemView.NoEditTriggers); self.table.horizontalHeader().setSectionResizeMode(2,QHeaderView.Stretch); self.table.doubleClicked.connect(lambda *_:self.open_file()); root.addWidget(self.table,1); self.status=QLabel(); root.addWidget(self.status); self.load()
    def load(self):
        q=self.search.text().strip(); with_dummy=0
        with get_session() as s:
            rows=s.execute(text("""SELECT id,document_no,title,document_type,entity_type,file_name,file_path FROM documents WHERE :q='' OR document_no LIKE :like OR title LIKE :like OR COALESCE(file_name,'') LIKE :like ORDER BY id DESC LIMIT 500"""),{"q":q,"like":f"%{q}%"}).all()
        self.table.setRowCount(0)
        for x in rows:
            r=self.table.rowCount(); self.table.insertRow(r)
            for c,v in enumerate(x):self.table.setItem(r,c,QTableWidgetItem("" if v is None else str(v)))
        self.status.setText(f"السجلات: {len(rows):,}")
    def add(self):
        d=QDialog(self); d.setWindowTitle("إضافة مستند"); f=QFormLayout(d); no=QLineEdit(); title=QLineEdit(); typ=QLineEdit(); entity=QLineEdit(); file_name=QLineEdit(); file_path=QLineEdit(); choose=QPushButton("اختيار ملف"); choose.clicked.connect(lambda:self.pick(file_name,file_path)); f.addRow("رقم المستند:",no); f.addRow("العنوان:",title); f.addRow("النوع:",typ); f.addRow("نوع الكيان:",entity); f.addRow("اسم الملف:",file_name); f.addRow("المسار:",file_path); f.addRow(choose); b=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); b.accepted.connect(d.accept); b.rejected.connect(d.reject); f.addRow(b)
        if d.exec()!=QDialog.Accepted:return
        try:
            with get_session() as s:
                s.execute(text("INSERT INTO documents(document_no,title,document_type,entity_type,file_name,file_path,created_at) VALUES(:n,:t,:ty,:e,:fn,:fp,CURRENT_TIMESTAMP)"),{"n":no.text().strip(),"t":title.text().strip(),"ty":typ.text().strip() or None,"e":entity.text().strip() or None,"fn":file_name.text().strip() or None,"fp":file_path.text().strip() or None}); s.commit()
            self.load()
        except Exception as e:QMessageBox.critical(self,"فشل الحفظ",str(e))
    def pick(self,name,path):
        p,_=QFileDialog.getOpenFileName(self,"اختيار مرفق")
        if p:name.setText(p.split("/")[-1].split("\\\\")[-1]); path.setText(p)
    def open_file(self):
        r=self.table.currentRow()
        if r<0:return
        p=self.table.item(r,6).text() if self.table.item(r,6) else ""
        if p and QDesktopServices.openUrl(QUrl.fromLocalFile(p)):return
        QMessageBox.information(self,"المرفق","مسار الملف غير موجود أو لا يمكن فتحه.")
