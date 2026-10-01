from app.ui.theme import APP_STYLE
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QInputDialog, QMessageBox, QTableWidget, QTableWidgetItem
)
from app.services.treasury_operations_service import TreasuryOperationsService
from app.services.permission_service import PermissionService


class TreasuryAccountsWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(APP_STYLE)
        self.setStyleSheet(APP_STYLE)
        self.setWindowTitle("حسابات الخزينة والبنوك")
        self.setMinimumSize(1000, 650)
        layout = QVBoxLayout(self)

        title = QLabel("حسابات الخزينة والبنوك")
        title.setStyleSheet("font-size:26px;font-weight:bold")
        layout.addWidget(title)

        actions = QHBoxLayout()
        for label, handler in (
            ("تحديث", self.refresh),
            ("تحويل بين الحسابات", self.transfer),
            ("كشف الحساب", self.statement),
        ):
            b = QPushButton(label)
            b.clicked.connect(handler)
            actions.addWidget(b)
        layout.addLayout(actions)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["المعرف", "الرمز", "الحساب", "النوع", "الحساب المحاسبي", "الرصيد"]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

        self.refresh()

    def _user(self):
        uid = PermissionService.default_user_id()
        if uid is None:
            raise ValueError("لا يوجد مستخدم فعّال في النظام")
        return uid

    def refresh(self):
        try:
            rows = TreasuryOperationsService.list_accounts()
            self.table.setRowCount(0)
            for row in rows:
                r = self.table.rowCount()
                self.table.insertRow(r)
                values = [
                    row["id"], row["code"], row["name_ar"],
                    row["account_type"], row["gl_account_code"],
                    f"{TreasuryOperationsService.balance(row['id']):.2f}",
                ]
                for c, value in enumerate(values):
                    self.table.setItem(r, c, QTableWidgetItem(str(value)))
            self.table.resizeColumnsToContents()
        except Exception as exc:
            QMessageBox.critical(self, "فشل تحديث الخزينة", str(exc))

    def _selected_id(self):
        row = self.table.currentRow()
        if row < 0:
            raise ValueError("حدد حساب خزينة أولًا")
        return int(self.table.item(row, 0).text())

    def transfer(self):
        try:
            rows = TreasuryOperationsService.list_accounts()
            if len(rows) < 2:
                raise ValueError("يلزم وجود حسابي خزينة نشطين على الأقل")
            labels = [f"{r['id']} - {r['name_ar']} ({r['code']})" for r in rows]
            src, ok = QInputDialog.getItem(self, "الحساب المصدر", "من:", labels, 0, False)
            if not ok:
                return
            dst, ok = QInputDialog.getItem(self, "الحساب المستلم", "إلى:", labels, 1 if len(labels) > 1 else 0, False)
            if not ok:
                return
            source_id = int(src.split(" - ", 1)[0])
            dest_id = int(dst.split(" - ", 1)[0])
            amount, ok = QInputDialog.getDouble(
                self, "التحويل", "المبلغ:", 0, 0.01, 999999999, 2
            )
            if not ok:
                return
            notes, ok = QInputDialog.getText(self, "التحويل", "ملاحظات:")
            if not ok:
                return
            result = TreasuryOperationsService.transfer(
                source_id, dest_id, amount, self._user(), notes or None
            )
            QMessageBox.information(
                self, "تم التحويل",
                f"تم التحويل بنجاح\nرقم التحويل: {result['transfer_number']}\n"
                f"القيمة: {result['amount']:.2f}"
            )
            self.refresh()
        except Exception as exc:
            QMessageBox.critical(self, "فشل التحويل", str(exc))

    def statement(self):
        try:
            account_id = self._selected_id()
            rows = TreasuryOperationsService.statement(account_id, 100)
            if not rows:
                QMessageBox.information(self, "كشف الحساب", "لا توجد حركات مسجلة لهذا الحساب.")
                return
            lines = []
            for row in rows:
                lines.append(
                    f"{row['created_at']} | {row['movement_type']} | "
                    f"{row['amount']:.2f} | {row['document_number']}"
                )
            QMessageBox.information(self, "كشف الحساب", "\n".join(lines))
        except Exception as exc:
            QMessageBox.critical(self, "فشل كشف الحساب", str(exc))

# UI reference theme is applied by the main application shell.
