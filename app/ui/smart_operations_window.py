from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QLabel,QLineEdit,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QMessageBox
from sqlalchemy import text
from app.database.connection import get_session
from app.ui.theme import APP_STYLE
from app.ui.i18n import display_value

class SmartOperationsWindow(QWidget):
    """مركز التنبيهات في شكل جدول تشغيلي واضح."""
    def __init__(self,user=None,parent=None):
        super().__init__(parent);self.setWindowTitle('التنبيهات');self.setMinimumSize(1200,720);self.setLayoutDirection(Qt.RightToLeft);self.setStyleSheet(APP_STYLE);root=QVBoxLayout(self);h=QHBoxLayout();h.addWidget(QLabel('التنبيهات'));h.addStretch();self.search=QLineEdit();self.search.setPlaceholderText('بحث في التنبيهات');h.addWidget(self.search);b=QPushButton('تحديث');b.clicked.connect(self.load);h.addWidget(b);read=QPushButton('تحديد كمقروء');read.clicked.connect(self.mark_read);h.addWidget(read);root.addLayout(h);self.table=QTableWidget();self.table.setSelectionBehavior(QAbstractItemView.SelectRows);self.table.setAlternatingRowColors(True);root.addWidget(self.table,1);self.status=QLabel('جاهز');root.addWidget(self.status);self.search.textChanged.connect(lambda *_:self.load());self.load()
    def load(self):
        try:
            with get_session() as s:
                cols=[r[1] for r in s.connection().exec_driver_sql('PRAGMA table_info(notifications)').fetchall()]
                if not cols:self.status.setText('جدول التنبيهات غير موجود');return
                preferred=[x for x in ['id','type','title','message','severity','status','is_read','created_at'] if x in cols]
                q=self.search.text().strip();where='';params={}
                if q:
                    textcols=[x for x in preferred if x not in {'id','created_at','is_read'}];where=' WHERE '+' OR '.join(f'CAST("{x}" AS TEXT) LIKE :q' for x in textcols);params['q']=f'%{q}%'
                rows=s.execute(text(f'SELECT {",".join(chr(34)+x+chr(34) for x in preferred)} FROM notifications{where} ORDER BY rowid DESC LIMIT 500'),params).all()
            self.table.setColumnCount(len(preferred));self.table.setHorizontalHeaderLabels([{'id':'الرقم','type':'النوع','title':'العنوان','message':'التفاصيل','severity':'الخطورة','status':'الحالة','is_read':'مقروء','created_at':'التاريخ'}.get(x,x) for x in preferred]);self.table.setRowCount(0)
            for row in rows:
                r=self.table.rowCount();self.table.insertRow(r)
                for c,v in enumerate(row):self.table.setItem(r,c,QTableWidgetItem(display_value(v)))
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents);self.table.horizontalHeader().setStretchLastSection(True);self.status.setText(f'عدد التنبيهات: {len(rows)}')
        except Exception as e:QMessageBox.critical(self,'التنبيهات',str(e))
    def mark_read(self):
        r=self.table.currentRow();
        if r<0:return
        id_col=next((i for i in range(self.table.columnCount()) if self.table.horizontalHeaderItem(i).text()=='الرقم'),None)
        if id_col is None:return
        rid=int(self.table.item(r,id_col).text())
        try:
            with get_session() as s:s.execute(text('UPDATE notifications SET is_read=1,status=COALESCE(status,\'READ\') WHERE id=:id'),{'id':rid});s.commit();self.load()
        except Exception as e:QMessageBox.critical(self,'فشل تحديث التنبيه',str(e))
