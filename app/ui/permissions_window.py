from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QTableWidget,
    QTableWidgetItem, QCheckBox, QPushButton, QMessageBox, QInputDialog
)
from sqlalchemy import text
from app.database.connection import get_session
from app.services.permission_service import PermissionService
from app.ui.theme import APP_STYLE
from app.ui.i18n import field_label

class PermissionsWindow(QWidget):
    """إدارة الأدوار والصلاحيات وإسناد الأدوار للمستخدمين."""

    PRESETS = {
        "cashier": "كاشير نقطة البيع",
        "sales": "موظف مبيعات",
        "inventory": "موظف مخزون",
        "accountant": "محاسب",
        "purchasing": "موظف مشتريات",
        "viewer": "مستخدم للعرض فقط",
        "admin": "مدير النظام",
    }

    def __init__(self, user=None, parent=None):
        super().__init__(parent)
        self.user = dict(user or {})
        self.setStyleSheet(APP_STYLE)
        self.setWindowTitle("الأدوار والصلاحيات")
        self.setMinimumSize(1250, 760)
        self.setLayoutDirection(Qt.RightToLeft)

        root = QVBoxLayout(self)

        top = QHBoxLayout()
        top.addWidget(QLabel("الدور:"))
        self.role = QComboBox()
        self.role.currentIndexChanged.connect(self.load)
        top.addWidget(self.role, 2)

        self.preset = QComboBox()
        self.preset.addItem("اختر دورًا جاهزًا", "")
        for code, name in self.PRESETS.items():
            self.preset.addItem(name, code)
        top.addWidget(self.preset, 2)

        new_role = QPushButton("إنشاء دور")
        new_role.clicked.connect(self.create_role)
        top.addWidget(new_role)

        save = QPushButton("حفظ الصلاحيات")
        save.setObjectName("Success")
        save.clicked.connect(self.save)
        top.addWidget(save)
        root.addLayout(top)

        assign = QHBoxLayout()
        assign.addWidget(QLabel("المستخدم:"))
        self.user = QComboBox()
        assign.addWidget(self.user, 2)
        assign_btn = QPushButton("إسناد الدور للمستخدم")
        assign_btn.clicked.connect(self.assign_role)
        assign.addWidget(assign_btn)
        self.user_status = QLabel()
        assign.addWidget(self.user_status, 2)
        root.addLayout(assign)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["الصلاحية", "الوصف", "ممنوحة"])
        self.table.setAlternatingRowColors(True)
        root.addWidget(self.table, 1)

        self.status = QLabel()
        root.addWidget(self.status)

        self.ensure_and_load()

    def ensure_and_load(self):
        try:
            with get_session() as s:
                PermissionService.ensure_schema(s)
                s.commit()
        except Exception as exc:
            QMessageBox.critical(self, "الصلاحيات", f"تعذر تجهيز نظام الصلاحيات: {exc}")
            return
        self.load_roles()
        self.load_users()

    def load_roles(self):
        with get_session() as s:
            rows = s.execute(text(
                "SELECT id,code,COALESCE(NULLIF(name_ar,''),code) AS display_name "
                "FROM erp_roles WHERE COALESCE(is_active,1)=1 ORDER BY id"
            )).all()
        current = self.role.currentData()
        self.role.blockSignals(True)
        self.role.clear()
        for rid, code, name in rows:
            self.role.addItem(str(name), int(rid))
        self.role.blockSignals(False)
        if current is not None:
            idx = self.role.findData(current)
            if idx >= 0:
                self.role.setCurrentIndex(idx)
        self.load()

    def load_users(self):
        with get_session() as s:
            rows = s.execute(text(
                "SELECT id,username FROM users "
                "WHERE COALESCE(is_active,1)=1 ORDER BY id"
            )).all()
        current = self.user.currentData()
        self.user.clear()
        for uid, username in rows:
            self.user.addItem(str(username), int(uid))
        if current is not None:
            idx = self.user.findData(current)
            if idx >= 0:
                self.user.setCurrentIndex(idx)
        self.update_user_status()

    def load(self, *_):
        rid = self.role.currentData()
        if rid is None:
            self.table.setRowCount(0)
            return
        with get_session() as s:
            perms = s.execute(text(
                "SELECT id,code,COALESCE(NULLIF(name_ar,''),code) AS name_ar,"
                "COALESCE(NULLIF(name_ar,''),code) AS description "
                "FROM erp_permissions WHERE COALESCE(is_active,1)=1 "
                "ORDER BY code,id"
            )).mappings().all()
            granted = {
                int(row[0]) for row in s.execute(
                    text("SELECT permission_id FROM erp_role_permissions WHERE role_id=:r"),
                    {"r": int(rid)}
                ).all()
            }
        self.table.setRowCount(0)
        for p in perms:
            row = self.table.rowCount()
            self.table.insertRow(row)
            label = str(p["name_ar"] or field_label(p["code"]))
            self.table.setItem(row, 0, QTableWidgetItem(label))
            self.table.setItem(row, 1, QTableWidgetItem(str(p["description"] or label)))
            box = QCheckBox()
            box.setChecked(int(p["id"]) in granted)
            box.setProperty("permission_id", int(p["id"]))
            self.table.setCellWidget(row, 2, box)
        self.status.setText(f"الصلاحيات المتاحة: {len(perms):,}")

    def create_role(self):
        name, ok = QInputDialog.getText(self, "إنشاء دور", "اسم الدور الجديد:")
        if not ok or not name.strip():
            return
        code, ok = QInputDialog.getText(self, "رمز الدور", "رمز داخلي بالإنجليزية، مثال: cashier2:")
        if not ok or not code.strip():
            return
        code = code.strip().lower().replace(" ", "_")
        try:
            uid=self.user.get('id') or self.user.get('user_id')
            rid=PermissionService.create_role(uid, code, name.strip())
            self.load_roles()
            idx = self.role.findText(name.strip())
            if idx >= 0:
                self.role.setCurrentIndex(idx)
            QMessageBox.information(self, "تم", "تم إنشاء الدور.")
        except Exception as exc:
            QMessageBox.critical(self, "تعذر إنشاء الدور", str(exc))

    def save(self):
        rid = self.role.currentData()
        if rid is None:
            return
        try:
            uid=self.user.get('id') or self.user.get('user_id')
            permission_ids=[]
            for row in range(self.table.rowCount()):
                box=self.table.cellWidget(row,2)
                if box and box.isChecked():
                    permission_ids.append(int(box.property("permission_id")))
            PermissionService.set_role_permissions(uid, int(rid), permission_ids)
            QMessageBox.information(self, "تم", "تم حفظ صلاحيات الدور.")
            self.load()
        except Exception as exc:
            QMessageBox.critical(self, "فشل الحفظ", str(exc))

    def assign_role(self):
        uid = self.user.currentData()
        rid = self.role.currentData()
        if uid is None or rid is None:
            QMessageBox.warning(self, "الصلاحيات", "حدد المستخدم والدور أولًا.")
            return
        try:
            actor=self.user.get('id') or self.user.get('user_id')
            PermissionService.assign_role(actor, int(uid), int(rid))
            self.update_user_status()
            QMessageBox.information(self, "تم", "تم إسناد الدور للمستخدم.")
        except Exception as exc:
            QMessageBox.critical(self, "فشل الإسناد", str(exc))

    def update_user_status(self):
        uid = self.user.currentData()
        if uid is None:
            self.user_status.setText("")
            return
        with get_session() as s:
            rows = s.execute(text(
                "SELECT COALESCE(NULLIF(r.name_ar,''),r.code) "
                "FROM erp_user_roles ur JOIN erp_roles r ON r.id=ur.role_id "
                "WHERE ur.user_id=:u ORDER BY r.id"
            ), {"u": int(uid)}).all()
        self.user_status.setText("الدور الحالي: " + ("، ".join(str(x[0]) for x in rows) if rows else "بدون دور"))
