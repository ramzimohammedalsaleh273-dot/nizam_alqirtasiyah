from app.ui.theme import APP_STYLE
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QTableWidget,QTableWidgetItem,QTabWidget,QMessageBox
from sqlalchemy import text
from app.database.connection import get_session


class DataWindow(QWidget):
    """واجهة تشغيلية عامة للوحدات الإدارية والمالية تعتمد على الجداول الفعلية."""
    def __init__(self,title,sections,parent=None):
        super().__init__(parent)
        self.setStyleSheet(APP_STYLE); self.title=title; self.sections=sections
        self.setWindowTitle(title); self.setMinimumSize(1100,650)
        root=QVBoxLayout(self); h=QHBoxLayout()
        label=QLabel(title); label.setStyleSheet("font-size:28px;font-weight:bold")
        h.addWidget(label); h.addStretch()
        b=QPushButton("تحديث"); b.clicked.connect(self.load); h.addWidget(b)
        root.addLayout(h)
        self.tabs=QTabWidget(); root.addWidget(self.tabs); self.tables={}
        for key,caption,table in sections:
            w=QWidget(); lay=QVBoxLayout(w); t=QTableWidget(); t.setEditTriggers(QTableWidget.NoEditTriggers)
            lay.addWidget(t); self.tabs.addTab(w,caption); self.tables[key]=(t,table)
        self.load()

    @staticmethod
    def columns(session,table):
        return [r[1] for r in session.execute(text(f'PRAGMA table_info("{table}")')).fetchall()]

    def load(self):
        try:
            with get_session() as s:
                for key,(widget,table) in self.tables.items():
                    exists=s.execute(text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:t"),{"t":table}).scalar()
                    if not exists:
                        widget.setColumnCount(1); widget.setHorizontalHeaderLabels(["الحالة"])
                        widget.setRowCount(1); widget.setItem(0,0,QTableWidgetItem("الجدول غير موجود"))
                        continue
                    cols=self.columns(s,table)
                    cols=cols[:18]
                    if not cols: continue
                    rows=s.execute(text('SELECT '+','.join('"'+c+'"' for c in cols)+' FROM "'+table+'" ORDER BY rowid DESC LIMIT 200')).fetchall()
                    widget.setColumnCount(len(cols)); widget.setHorizontalHeaderLabels(cols); widget.setRowCount(0)
                    for row in rows:
                        i=widget.rowCount(); widget.insertRow(i)
                        for j,v in enumerate(row):
                            widget.setItem(i,j,QTableWidgetItem("" if v is None else str(v)))
                    widget.resizeColumnsToContents()
        except Exception as exc:
            QMessageBox.critical(self,"خطأ",str(exc))


def accounting_window(parent=None):
    return DataWindow("المحاسبة",[
        ("entries","القيود اليومية","journal_entries"),
        ("lines","تفاصيل القيود","journal_entry_lines"),
        ("accounts","دليل الحسابات","accounts"),
    ],parent)


def treasury_window(parent=None):
    from app.ui.treasury_operations_window import TreasuryOperationsWindow
    return TreasuryOperationsWindow(parent)


def employees_window(parent=None):
    return DataWindow("الموظفون والمستخدمون",[
        ("users","المستخدمون","users"),
        ("roles","الأدوار","erp_roles"),
        ("permissions","الصلاحيات","erp_permissions"),
        ("sessions","جلسات الدخول","erp_login_sessions"),
    ],parent)


def settings_window(parent=None):
    return DataWindow("الإعدادات",[
        ("system","إعدادات النظام","system_settings"),
        ("sequences","تسلسلات المستندات","document_sequences"),
        ("periods","الفترات المحاسبية","fiscal_periods"),
        ("audit","سجل التدقيق","audit_logs"),
    ],parent)
