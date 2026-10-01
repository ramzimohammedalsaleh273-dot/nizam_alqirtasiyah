from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QTableWidget,QTableWidgetItem,QCheckBox,QPushButton,QMessageBox
from sqlalchemy import text
from app.database.connection import get_session
from app.ui.theme import APP_STYLE

class PermissionsWindow(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent); self.setStyleSheet(APP_STYLE); self.setWindowTitle("الأدوار والصلاحيات"); self.setMinimumSize(1250,720); self.setLayoutDirection(Qt.RightToLeft)
        root=QVBoxLayout(self); h=QHBoxLayout(); t=QLabel("مصفوفة الصلاحيات"); t.setObjectName("SectionTitle"); h.addWidget(t); h.addStretch(); self.role=QComboBox(); self.role.currentIndexChanged.connect(self.load); h.addWidget(QLabel("الدور:")); h.addWidget(self.role); save=QPushButton("حفظ الصلاحيات"); save.setObjectName("Success"); save.clicked.connect(self.save); h.addWidget(save); root.addLayout(h)
        self.table=QTableWidget(0,3); self.table.setHorizontalHeaderLabels(["الوحدة / الصلاحية","الوصف","ممنوحة"]); self.table.setAlternatingRowColors(True); root.addWidget(self.table,1); self.status=QLabel(); root.addWidget(self.status); self.load_roles()
    def load_roles(self):
        with get_session() as s:
            self.role.clear()
            for r in s.execute(text("SELECT id,name FROM roles WHERE COALESCE(is_active,1)=1 ORDER BY id")).all(): self.role.addItem(str(r[1]),int(r[0]))
        self.load()
    def load(self,*_):
        rid=self.role.currentData()
        if rid is None:return
        with get_session() as s:
            perms=s.execute(text("SELECT id,code,name,description,module,action FROM permissions ORDER BY module,action,id")).mappings().all()
            granted={int(x[0]) for x in s.execute(text("SELECT permission_id FROM role_permissions WHERE role_id=:r"),{"r":rid}).all()}
        self.table.setRowCount(0); self.table.setColumnCount(3)
        for p in perms:
            r=self.table.rowCount(); self.table.insertRow(r)
            self.table.setItem(r,0,QTableWidgetItem(f"{p['name']} — {p['code']}"))
            self.table.setItem(r,1,QTableWidgetItem(p.get("description") or f"{p['module']} / {p['action']}"))
            box=QCheckBox(); box.setChecked(int(p["id"]) in granted); box.setProperty("permission_id",int(p["id"])); self.table.setCellWidget(r,2,box)
        self.status.setText(f"الصلاحيات المتاحة: {len(perms):,}")
    def save(self):
        rid=self.role.currentData()
        if rid is None:return
        try:
            with get_session() as s:
                s.execute(text("DELETE FROM role_permissions WHERE role_id=:r"),{"r":rid})
                for r in range(self.table.rowCount()):
                    box=self.table.cellWidget(r,2)
                    if box and box.isChecked(): s.execute(text("INSERT INTO role_permissions(role_id,permission_id) VALUES(:r,:p)"),{"r":rid,"p":box.property("permission_id")})
                s.commit()
            QMessageBox.information(self,"تم","تم حفظ مصفوفة الصلاحيات للدور المحدد."); self.load()
        except Exception as e: QMessageBox.critical(self,"فشل الحفظ",str(e))
