from app.ui.theme import APP_STYLE
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QTableWidget, QTableWidgetItem,
    QLabel, QPushButton, QHBoxLayout, QMessageBox, QDialog, QFormLayout,
    QLineEdit, QDoubleSpinBox, QComboBox, QCheckBox, QTextEdit,
    QDialogButtonBox, QAbstractItemView, QTabWidget, QHeaderView
)
from app.services.party_service import PartyService
from app.services.party_master_service import PartyMasterService


class PartyDialog(QDialog):
    """نموذج موحد وكامل لإدخال بيانات العميل أو المورد."""

    def __init__(self, supplier=False, groups=None, party=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(APP_STYLE)
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



class PartyCardDialog(QDialog):
    """بطاقة العميل/المورد المرجعية مع البيانات والفواتير والمرتجعات والدفعات وكشف الحساب والمستندات والملاحظات."""
    def __init__(self, party_id, supplier=False, parent=None):
        super().__init__(parent)
        self.party_id=int(party_id); self.supplier=supplier
        self.setWindowTitle("بطاقة المورد" if supplier else "بطاقة العميل")
        self.setMinimumSize(1180,760); self.setLayoutDirection(Qt.RightToLeft); self.setStyleSheet(APP_STYLE)
        root=QVBoxLayout(self); self.title=QLabel("بطاقة الطرف"); self.title.setObjectName("SectionTitle"); root.addWidget(self.title)
        self.meta=QLabel(""); root.addWidget(self.meta)
        self.tabs=QTabWidget(); root.addWidget(self.tabs,1)
        self._build()

    def _safe(self, sql, params):
        try:
            from sqlalchemy import text
            from app.database.connection import get_session
            with get_session() as s:
                return s.execute(text(sql),params).mappings().all()
        except Exception:
            return []

    def _table(self, headers, rows):
        t=QTableWidget(0,len(headers)); t.setHorizontalHeaderLabels(headers); t.setSelectionBehavior(QAbstractItemView.SelectRows); t.setEditTriggers(QAbstractItemView.NoEditTriggers); t.setAlternatingRowColors(True); t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents); t.horizontalHeader().setStretchLastSection(True)
        for row in rows:
            r=t.rowCount(); t.insertRow(r)
            for col,v in enumerate(row): t.setItem(r,col,QTableWidgetItem("" if v is None else str(v)))
        return t

    def _add(self,title,headers,rows): self.tabs.addTab(self._table(headers,rows),title)

    def _build(self):
        table="suppliers" if self.supplier else "customers"
        with get_session() as s:
            p=s.execute(text(f'SELECT * FROM "{table}" WHERE id=:id'),{"id":self.party_id}).mappings().first()
        if not p:
            self.title.setText("السجل غير موجود"); return
        name=p.get("name") or "—"; code=p.get("supplier_code") or p.get("customer_code") or p.get("party_code") or p.get("code") or "—"
        self.title.setText(f"بطاقة {'المورد' if self.supplier else 'العميل'}: {name}")
        self.meta.setText(f"الكود: {code}   |   الهاتف: {p.get('phone') or p.get('mobile') or '—'}   |   الرصيد: {p.get('current_balance') or 0}")
        self._add("البيانات",["الحقل","القيمة"],[(k,v) for k,v in p.items() if k not in {"id","created_at","updated_at","notes"}])
        if self.supplier:
            inv=self._safe("SELECT invoice_date,invoice_number,total_amount,paid_amount,due_amount,status FROM purchase_invoices WHERE supplier_id=:id ORDER BY id DESC LIMIT 500",{"id":self.party_id})
            ret=self._safe("SELECT created_at,return_number,total_amount,status,reason FROM purchase_returns WHERE supplier_id=:id ORDER BY id DESC LIMIT 500",{"id":self.party_id})
            pays=self._safe("SELECT payment_date,payment_number,amount,payment_method,reference_number,notes FROM cash_payments WHERE supplier_id=:id ORDER BY id DESC LIMIT 500",{"id":self.party_id})
            tx=self._safe("SELECT created_at,transaction_type,amount,reference_type,reference_id,balance_after FROM supplier_transactions WHERE supplier_id=:id ORDER BY id DESC LIMIT 500",{"id":self.party_id})
        else:
            inv=self._safe("SELECT created_at,invoice_number,total_amount,paid_amount,due_amount,status FROM sales WHERE customer_id=:id ORDER BY id DESC LIMIT 500",{"id":self.party_id})
            ret=self._safe("SELECT created_at,return_number,total_amount,status,reason FROM sale_returns WHERE customer_id=:id ORDER BY id DESC LIMIT 500",{"id":self.party_id})
            pays=self._safe("SELECT payment_date,payment_number,amount,payment_method,reference_number,notes FROM customer_payments WHERE customer_id=:id ORDER BY id DESC LIMIT 500",{"id":self.party_id})
            tx=self._safe("SELECT created_at,transaction_type,amount,reference_type,reference_id,balance_after FROM customer_transactions WHERE customer_id=:id ORDER BY id DESC LIMIT 500",{"id":self.party_id})
        self._add("المشتريات" if self.supplier else "الفواتير",list(inv[0].keys()) if inv else ["لا توجد سجلات"],[tuple(x.values()) for x in inv] if inv else [])
        self._add("المرتجعات",list(ret[0].keys()) if ret else ["لا توجد سجلات"],[tuple(x.values()) for x in ret] if ret else [])
        self._add("الدفعات",list(pays[0].keys()) if pays else ["لا توجد سجلات"],[tuple(x.values()) for x in pays] if pays else [])
        self._add("كشف الحساب",list(tx[0].keys()) if tx else ["لا توجد حركات"],[tuple(x.values()) for x in tx] if tx else [])
        docs=self._safe("SELECT document_no,title,document_type,file_name,file_path,created_at FROM documents WHERE entity_type=:etype AND entity_id=:id ORDER BY id DESC",{"etype":"supplier" if self.supplier else "customer","id":self.party_id})
        self._add("المستندات",list(docs[0].keys()) if docs else ["لا توجد مستندات"],[tuple(x.values()) for x in docs] if docs else [])
        self._add("الملاحظات",["البيان","النص"],[("ملاحظات",p.get("notes"))])


class PartiesWindow(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("العملاء والموردون")
        self.setMinimumSize(1150, 650)

        layout = QVBoxLayout(self)
        self.setLayoutDirection(Qt.RightToLeft)
        title = QLabel("إدارة العملاء والموردين")
        title.setStyleSheet("font-size:28px;font-weight:bold")
        layout.addWidget(title)

        bar = QHBoxLayout()
        self.add_customer_button = QPushButton("إضافة عميل")
        self.add_supplier_button = QPushButton("إضافة مورد")
        self.open_button = QPushButton("فتح البطاقة")
        self.open_button.clicked.connect(self.open_card)
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
        bar.addWidget(self.open_button)
        bar.addWidget(self.edit_button)
        bar.addWidget(self.delete_button)
        bar.addWidget(self.refresh_button)
        bar.addStretch()
        layout.addLayout(bar)

        search_row=QHBoxLayout()
        search_row.addWidget(QLabel("بحث لحظي:"))
        self.search=QLineEdit(); self.search.setPlaceholderText("رقم العميل أو الاسم أو الهاتف أو البريد…"); self.search.textChanged.connect(lambda _: self.load())
        search_row.addWidget(self.search,1); layout.addLayout(search_row)

        self.tabs = QTabWidget()
        self.customers = self._table()
        self.suppliers = self._table()
        self.tabs.addTab(self.customers, "العملاء")
        self.tabs.addTab(self.suppliers, "الموردون")
        layout.addWidget(self.tabs)

        self.customers.cellDoubleClicked.connect(lambda *_: self.open_card())
        self.suppliers.cellDoubleClicked.connect(lambda *_: self.open_card())
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
        table.setWordWrap(False)
        table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        table.setMinimumHeight(430)
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
                {"individual":"فرد","company":"شركة","school":"مدرسة","government":"جهة حكومية","local":"محلي","international":"دولي","manufacturer":"مصنّع","distributor":"موزع"}.get(str(row_data.get("party_type") or ""), row_data.get("party_type") or ""),
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
            term=self.search.text().strip().lower()
            customers=PartyService.customers()
            suppliers=PartyService.suppliers()
            if term:
                def match(row):
                    return any(term in str(row.get(k) or "").lower() for k in ("id","party_code","name","phone","email","tax_number","address","current_balance"))
                customers=[r for r in customers if match(r)]
                suppliers=[r for r in suppliers if match(r)]
            self._populate(self.customers, customers)
            self._populate(self.suppliers, suppliers)
        except Exception as exc:
            QMessageBox.critical(self, "فشل تحميل الأطراف", str(exc))

    def open_card(self):
        supplier, party = self._selected()
        if party is None:
            QMessageBox.information(self,"البطاقة","اختر عميلًا أو موردًا أولًا."); return
        try:
            PartyCardDialog(party["id"], supplier=supplier, parent=self).exec()
        except Exception as exc:
            QMessageBox.critical(self,"فشل فتح البطاقة",str(exc))

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


# UI reference theme is applied by the main application shell.
