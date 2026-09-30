from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QTableWidget, QTableWidgetItem,
    QLabel, QPushButton, QHBoxLayout, QMessageBox, QDialog, QFormLayout,
    QLineEdit, QDoubleSpinBox, QComboBox, QCheckBox, QTextEdit,
    QDialogButtonBox, QAbstractItemView
)
from app.services.party_service import PartyService
from app.services.party_master_service import PartyMasterService


class PartyDialog(QDialog):
    """نموذج موحد وكامل لإدخال بيانات العميل أو المورد."""

    def __init__(self, supplier=False, groups=None, party=None, parent=None):
        super().__init__(parent)
        self.supplier = supplier
        self.party = party or {}
        self.setWindowTitle(
            ("تعديل المورد" if supplier else "تعديل العميل")
            if party else ("إضافة مورد" if supplier else "إضافة عميل")
        )
        self.setMinimumWidth(560)

        layout = QFormLayout(self)

        self.code = QLineEdit(str(self.party.get("party_code") or ""))
        self.name = QLineEdit(str(self.party.get("name") or ""))
        self.phone = QLineEdit(str(self.party.get("phone") or ""))
        self.email = QLineEdit(str(self.party.get("email") or ""))
        self.address = QLineEdit(str(self.party.get("address") or ""))
        self.tax_number = QLineEdit(str(self.party.get("tax_number") or ""))
        self.party_type = QComboBox()
        types = ["فرد", "شركة", "مدرسة", "جهة حكومية"] if not supplier else ["محلي", "دولي", "مصنّع", "موزع"]
        self.party_type.addItems(types)
        existing_type = self.party.get("party_type")
        if existing_type:
            mapping = {
                "individual": "فرد", "company": "شركة", "school": "مدرسة",
                "government": "جهة حكومية", "local": "محلي", "international": "دولي",
                "manufacturer": "مصنّع", "distributor": "موزع",
            }
            index = self.party_type.findText(mapping.get(existing_type, existing_type))
            if index >= 0:
                self.party_type.setCurrentIndex(index)

        self.group = QComboBox()
        self.group.addItem("بدون مجموعة", None)
        for row in groups or []:
            self.group.addItem(row["name"], row["id"])
        if self.party.get("group_id") is not None:
            index = self.group.findData(self.party["group_id"])
            if index >= 0:
                self.group.setCurrentIndex(index)

        self.credit_limit = QDoubleSpinBox()
        self.credit_limit.setMaximum(999999999)
        self.credit_limit.setDecimals(2)
        self.credit_limit.setValue(float(self.party.get("credit_limit") or 0))

        self.payment_terms = QLineEdit(str(self.party.get("payment_terms") or ""))
        self.payment_terms.setPlaceholderText("مثال: نقدي، 30 يومًا، 60 يومًا")
        self.currency = QLineEdit(str(self.party.get("currency_code") or "SAR"))
        self.account = QLineEdit(
            "" if self.party.get("accounting_account_id") is None
            else str(self.party.get("accounting_account_id"))
        )
        self.notes = QTextEdit(str(self.party.get("notes") or ""))
        self.active = QCheckBox("نشط")
        self.active.setChecked(bool(self.party.get("is_active", 1)))

        layout.addRow("الكود:", self.code)
        layout.addRow("الاسم:", self.name)
        layout.addRow("الهاتف / الجوال:", self.phone)
        layout.addRow("البريد الإلكتروني:", self.email)
        layout.addRow("العنوان:", self.address)
        layout.addRow("الرقم الضريبي:", self.tax_number)
        layout.addRow("النوع:", self.party_type)
        layout.addRow("المجموعة:", self.group)
        layout.addRow("حد الائتمان:", self.credit_limit)
        layout.addRow("شروط السداد:", self.payment_terms)
        layout.addRow("العملة:", self.currency)
        layout.addRow("الحساب المحاسبي:", self.account)
        layout.addRow("الحالة:", self.active)
        layout.addRow("ملاحظات:", self.notes)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def validate_and_accept(self):
        if not self.code.text().strip() or not self.name.text().strip():
            QMessageBox.warning(self, "بيانات ناقصة", "الكود والاسم مطلوبان.")
            return
        if self.credit_limit.value() < 0:
            QMessageBox.warning(self, "بيانات غير صحيحة", "حد الائتمان لا يمكن أن يكون سالبًا.")
            return
        account = self.account.text().strip()
        if account and not account.isdigit():
            QMessageBox.warning(self, "بيانات غير صحيحة", "معرف الحساب المحاسبي يجب أن يكون رقمًا.")
            return
        super().accept()

    def values(self):
        type_map = {
            "فرد": "individual", "شركة": "company", "مدرسة": "school",
            "جهة حكومية": "government", "محلي": "local", "دولي": "international",
            "مصنّع": "manufacturer", "موزع": "distributor",
        }
        return {
            "code": self.code.text().strip(),
            "name": self.name.text().strip(),
            "phone": self.phone.text().strip() or None,
            "email": self.email.text().strip() or None,
            "address": self.address.text().strip() or None,
            "tax_number": self.tax_number.text().strip() or None,
            "party_type": type_map.get(self.party_type.currentText(), self.party_type.currentText()),
            "group_id": self.group.currentData(),
            "credit_limit": self.credit_limit.value(),
            "payment_terms": self.payment_terms.text().strip() or None,
            "currency_code": self.currency.text().strip() or "SAR",
            "accounting_account_id": int(self.account.text()) if self.account.text().strip() else None,
            "is_active": self.active.isChecked(),
            "notes": self.notes.toPlainText().strip() or None,
        }


class PartiesWindow(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("العملاء والموردون")
        self.setMinimumSize(1150, 650)

        layout = QVBoxLayout(self)
        title = QLabel("إدارة العملاء والموردين")
        title.setStyleSheet("font-size:28px;font-weight:bold")
        layout.addWidget(title)

        bar = QHBoxLayout()
        self.add_customer_button = QPushButton("إضافة عميل")
        self.add_supplier_button = QPushButton("إضافة مورد")
        self.edit_button = QPushButton("تعديل المحدد")
        self.delete_button = QPushButton("تعطيل/حذف المحدد")
        self.refresh_button = QPushButton("تحديث")
        self.add_customer_button.clicked.connect(self.add_customer)
        self.add_supplier_button.clicked.connect(self.add_supplier)
        self.edit_button.clicked.connect(self.edit_selected)
        self.delete_button.clicked.connect(self.delete_selected)
        self.refresh_button.clicked.connect(self.load)
        bar.addWidget(self.add_customer_button)
        bar.addWidget(self.add_supplier_button)
        bar.addWidget(self.edit_button)
        bar.addWidget(self.delete_button)
        bar.addWidget(self.refresh_button)
        bar.addStretch()
        layout.addLayout(bar)

        self.tabs = QTabWidget()
        self.customers = self._table()
        self.suppliers = self._table()
        self.tabs.addTab(self.customers, "العملاء")
        self.tabs.addTab(self.suppliers, "الموردون")
        layout.addWidget(self.tabs)

        self.customers.cellDoubleClicked.connect(lambda *_: self.edit_selected())
        self.suppliers.cellDoubleClicked.connect(lambda *_: self.edit_selected())
        self.load()

    @staticmethod
    def _table():
        table = QTableWidget(0, 9)
        table.setHorizontalHeaderLabels([
            "المعرف", "الكود", "الاسم", "النوع", "المجموعة",
            "الهاتف", "البريد", "حد الائتمان", "الرصيد"
        ])
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setStretchLastSection(True)
        return table

    def _populate(self, table, rows):
        table.setRowCount(0)
        for row_data in rows:
            row = table.rowCount()
            table.insertRow(row)
            values = [
                row_data.get("id"),
                row_data.get("party_code"),
                row_data.get("name"),
                row_data.get("party_type") or "",
                row_data.get("group_name") or "",
                row_data.get("phone") or "",
                row_data.get("email") or "",
                f'{float(row_data.get("credit_limit") or 0):.2f}',
                f'{float(row_data.get("current_balance") or 0):.2f}',
            ]
            for col, value in enumerate(values):
                table.setItem(row, col, QTableWidgetItem(str(value)))

    def load(self):
        try:
            self._populate(self.customers, PartyService.customers())
            self._populate(self.suppliers, PartyService.suppliers())
        except Exception as exc:
            QMessageBox.critical(self, "فشل تحميل الأطراف", str(exc))

    def _selected(self):
        supplier = self.tabs.currentIndex() == 1
        table = self.suppliers if supplier else self.customers
        row = table.currentRow()
        if row < 0:
            return supplier, None
        item = table.item(row, 0)
        if item is None:
            return supplier, None
        party_id = int(item.text())
        party = PartyService.get_party("suppliers" if supplier else "customers", party_id)
        return supplier, party

    def _open_form(self, supplier, party=None):
        groups = PartyService.groups(supplier=supplier)
        dialog = PartyDialog(supplier=supplier, groups=groups, party=party, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        values = dialog.values()
        try:
            table = "suppliers" if supplier else "customers"
            if party:
                PartyMasterService.update_party(table, party["id"], **values)
            elif supplier:
                PartyMasterService.create_supplier(
                    values["code"], values["name"], values["phone"],
                    values["credit_limit"], **{k: v for k, v in values.items() if k not in {"code", "name", "phone", "credit_limit"}}
                )
            else:
                PartyMasterService.create_customer(
                    values["code"], values["name"], values["phone"],
                    values["credit_limit"], **{k: v for k, v in values.items() if k not in {"code", "name", "phone", "credit_limit"}}
                )
            self.load()
        except Exception as exc:
            QMessageBox.critical(self, "فشل الحفظ", str(exc))

    def delete_selected(self):
        supplier, party = self._selected()
        if party is None:
            QMessageBox.information(self, "الحذف", "اختر عميلًا أو موردًا أولًا.")
            return
        label = "المورد" if supplier else "العميل"
        if QMessageBox.question(self, "تعطيل الطرف", f"سيتم إخفاء {label} من التشغيل مع الاحتفاظ بتاريخه. هل تريد المتابعة؟", QMessageBox.Yes|QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            PartyMasterService.deactivate_party("suppliers" if supplier else "customers", party["id"])
            self.load()
        except Exception as exc:
            QMessageBox.critical(self, "تعذر التعطيل", str(exc))

    def add_customer(self):
        self._open_form(False)

    def add_supplier(self):
        self._open_form(True)

    def edit_selected(self):
        supplier, party = self._selected()
        if party is None:
            QMessageBox.information(self, "التعديل", "اختر عميلًا أو موردًا أولًا.")
            return
        self._open_form(supplier, party)

