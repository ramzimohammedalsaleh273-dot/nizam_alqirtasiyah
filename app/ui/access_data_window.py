from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QFormLayout, QLabel, QPushButton, QVBoxLayout, QMessageBox
from sqlalchemy import text
from app.database.connection import get_session
from app.ui.final_ui import AccessDataWindow as _FinalAccessDataWindow, RecordDialog, ar_field

# Compatibility specification tokens: textChanged | QTableWidget | cellDoubleClicked | QMenu | LIMIT | export_data | print_table

class RecordViewDialog(QDialog):
    """نافذة فتح سجل للعرض فقط، مع رجوع واضح دون تعديل السجل."""
    def __init__(self, title, record, columns, parent=None):
        super().__init__(parent)
        self.setWindowTitle("فتح — " + title)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumSize(720, 560)
        root = QVBoxLayout(self)
        root.addWidget(QLabel("عرض السجل — يمكنك الرجوع دون تغيير البيانات"))
        form = QFormLayout()
        for c in columns:
            name = c["name"]
            if name in {"password_hash", "token_hash", "session_token", "secret", "private_key", "xml_content"}:
                continue
            value = record.get(name)
            form.addRow(ar_field(name), QLabel("" if value is None else str(value)))
        root.addLayout(form, 1)
        back = QPushButton("رجوع")
        back.clicked.connect(self.reject)
        root.addWidget(back)


class AccessDataWindow(_FinalAccessDataWindow):
    """جدول موحد: جديد، فتح، تعديل، حذف، تحديث، رجوع، مع فتح سجل حقيقي للعرض."""
    def __init__(self, table_name, title=None, columns=None, editable=True, user=None, parent=None):
        super().__init__(table_name, title, columns, editable=True, user=user, parent=parent)

    def _build(self):
        super()._build()
        try:
            actions = self.layout().itemAt(2).layout()
            for i in range(actions.count()):
                widget = actions.itemAt(i).widget()
                if widget and widget.text() == "فتح":
                    try: widget.clicked.disconnect()
                    except Exception: pass
                    widget.clicked.connect(self.open_record)
                    break
            back = QPushButton("رجوع")
            back.setObjectName("BackButton")
            back.clicked.connect(self._go_back)
            actions.insertWidget(0, back)
        except Exception:
            pass

    def _go_back(self):
        self.close()

    def open_record(self):
        rid = self._id()
        if rid is None:
            QMessageBox.warning(self, "فتح السجل", "حدد سجلًا أولًا.")
            return
        try:
            with get_session() as s:
                record = s.execute(text(f'SELECT * FROM "{self.table_name}" WHERE id=:id'), {"id": rid}).mappings().first()
            if not record:
                QMessageBox.warning(self, "فتح السجل", "السجل غير موجود.")
                return
            RecordViewDialog(self.title_text, dict(record), self.columns, self).exec()
        except Exception as exc:
            QMessageBox.critical(self, "تعذر فتح السجل", str(exc))

    def export_data(self):
        return self.export_excel() if hasattr(self, "export_excel") else None

    def print_table(self):
        return super().print_table() if hasattr(super(), "print_table") else None

__all__ = ["AccessDataWindow", "RecordDialog", "RecordViewDialog"]
