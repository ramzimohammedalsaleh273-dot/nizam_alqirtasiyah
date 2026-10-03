from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QTabWidget,QTableWidget,QTableWidgetItem,QLabel,QPushButton,QMessageBox,QDialog,QFormLayout,QLineEdit,QDoubleSpinBox,QComboBox,QCheckBox,QTextEdit,QDialogButtonBox,QAbstractItemView,QHeaderView
from sqlalchemy import text
from app.database.connection import get_session
from app.ui.theme import APP_STYLE
from app.ui.i18n import field_label, display_value

class PartyDialog(QDialog):
    def __init__(self,supplier=False,party=None,parent=None):
        super().__init__(parent); self.supplier=supplier; self.party=party or {}; self.setLayoutDirection(Qt.RightToLeft); self.setStyleSheet(APP_STYLE); self.setMinimumWidth(560); self.setWindowTitle(("تعديل المورد" if supplier else "تعديل العميل") if party else ("إضافة مورد" if supplier else "إضافة عميل")); f=QFormLayout(self)
        self.code=QLineEdit(str(self.party.get("party_code") or self.party.get("supplier_code") or self.party.get("customer_code") or "")); self.name=QLineEdit(str(self.party.get("name") or "")); self.phone=QLineEdit(str(self.party.get("phone") or "")); self.email=QLineEdit(str(self.party.get("email") or "")); self.address=QLineEdit(str(self.party.get("address") or "")); self.tax=QLineEdit(str(self.party.get("tax_number") or "")); self.kind=QComboBox(); self.kind.addItems(["فرد","شركة","مدرسة","جهة حكومية"] if not supplier else ["محلي","دولي","مصنّع","موزع"]); self.credit=QDoubleSpinBox(); self.credit.setMaximum(999999999); self.credit.setDecimals(2); self.credit.setValue(float(self.party.get("credit_limit") or 0)); self.terms=QLineEdit(str(self.party.get("payment_terms") or "")); self.currency=QLineEdit(str(self.party.get("currency_code") or "SAR")); self.notes=QTextEdit(str(self.party.get("notes") or "")); self.active=QCheckBox("نشط"); self.active.setChecked(bool(self.party.get("is_active",1)))
        for label,w in [("الكود:",self.code),("الاسم:",self.name),("الهاتف:",self.phone),("البريد:",self.email),("العنوان:",self.address),("الرقم الضريبي:",self.tax),("النوع:",self.kind),("حد الائتمان:",self.credit),("شروط السداد:",self.terms),("العملة:",self.currency),("الحالة:",self.active),("ملاحظات:",self.notes)]: f.addRow(label,w)
        b=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); b.accepted.connect(self._validate); b.rejected.connect(self.reject); f.addRow(b)
    def _validate(self):
        if not self.code.text().strip() or not self.name.text().strip(): QMessageBox.warning(self,"بيانات ناقصة","الكود والاسم مطلوبان."); return
        self.accept()
    def values(self): return {"code":self.code.text().strip(),"name":self.name.text().strip(),"phone":self.phone.text().strip() or None,"email":self.email.text().strip() or None,"address":self.address.text().strip() or None,"tax_number":self.tax.text().strip() or None,"party_type":self.kind.currentText(),"credit_limit":self.credit.value(),"payment_terms":self.terms.text().strip() or None,"currency_code":self.currency.text().strip() or "SAR","is_active":1 if self.active.isChecked() else 0,"notes":self.notes.toPlainText().strip() or None}

class PartyCardDialog(QDialog):
    def __init__(self,party_id,supplier=False,parent=None):
        super().__init__(parent); self.party_id=int(party_id); self.supplier=supplier; self.setLayoutDirection(Qt.RightToLeft); self.setStyleSheet(APP_STYLE); self.setMinimumSize(1180,760); self.setWindowTitle("بطاقة المورد" if supplier else "بطاقة العميل"); root=QVBoxLayout(self); self.title=QLabel(); self.title.setObjectName("SectionTitle"); root.addWidget(self.title); self.meta=QLabel(); root.addWidget(self.meta); self.tabs=QTabWidget(); root.addWidget(self.tabs,1); self._build()
    def _rows(self,sql,params):
        try:
            with get_session() as s: return s.execute(text(sql),params).mappings().all()
        except Exception: return []
    def _tab(self,title,rows,empty="لا توجد سجلات"):\n        headers=list(rows[0].keys()) if rows else [empty]\n        t=QTableWidget(0,len(headers))\n        t.setHorizontalHeaderLabels([field_label(h) for h in headers])\n        t.setEditTriggers(QAbstractItemView.NoEditTriggers)\n        t.setSelectionBehavior(QAbstractItemView.SelectRows)\n        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)\n        t.horizontalHeader().setStretchLastSection(True)\n        for row in rows:\n            r=t.rowCount(); t.insertRow(r)\n            for c,v in enumerate(row.values()):\n                t.setItem(r,c,QTableWidgetItem("" if v is None else display_value(v)))\n        self.tabs.addTab(t,title)\n\n    def _build(self):
        table="suppliers" if self.supplier else "customers"
        with get_session() as s: p=s.execute(text(f'SELECT * FROM "{table}" WHERE id=:id'),{"id":self.party_id}).mappings().first()
        if not p: self.title.setText("السجل غير موجود"); self.meta.setText("لم يتم العثور على الطرف المحدد."); return
        name=p.get("name") or "—"; code=p.get("supplier_code") or p.get("customer_code") or p.get("party_code") or "—"; self.title.setText(f"بطاقة {'المورد' if self.supplier else 'العميل'}: {name}"); self.meta.setText(f"الكود: {code} | الهاتف: {p.get('phone') or '—'} | الرصيد: {p.get('current_balance') or 0}")
        self._tab("البيانات",[{"الحقل":k,"القيمة":v} for k,v in p.items() if k not in {"id","created_at","updated_at"}],"لا توجد بيانات")
        if self.supplier:
            self._tab("الفواتير",self._rows("SELECT invoice_date,invoice_number,total_amount,paid_amount,due_amount,status FROM purchase_invoices WHERE supplier_id=:id ORDER BY id DESC LIMIT 500",{"id":self.party_id})); self._tab("المرتجعات",self._rows("SELECT created_at,return_number,total_amount,status,reason FROM purchase_returns WHERE supplier_id=:id ORDER BY id DESC LIMIT 500",{"id":self.party_id})); self._tab("الدفعات",self._rows("SELECT payment_date,payment_number,amount,payment_method,reference_number,notes FROM cash_payments WHERE supplier_id=:id ORDER BY id DESC LIMIT 500",{"id":self.party_id})); self._tab("كشف الحساب",self._rows("SELECT created_at,transaction_type,amount,reference_type,reference_id,balance_after FROM supplier_transactions WHERE supplier_id=:id ORDER BY id DESC LIMIT 500",{"id":self.party_id}))
        else:
            self._tab("الفواتير",self._rows("SELECT created_at,invoice_number,total_amount,paid_amount,due_amount,status FROM sales WHERE customer_id=:id ORDER BY id DESC LIMIT 500",{"id":self.party_id})); self._tab("المرتجعات",self._rows("SELECT created_at,return_number,total_amount,status,reason FROM sale_returns WHERE customer_id=:id ORDER BY id DESC LIMIT 500",{"id":self.party_id})); self._tab("الدفعات",self._rows("SELECT payment_date,payment_number,amount,payment_method,reference_number,notes FROM customer_payments WHERE customer_id=:id ORDER BY id DESC LIMIT 500",{"id":self.party_id})); self._tab("كشف الحساب",self._rows("SELECT created_at,transaction_type,amount,reference_type,reference_id,balance_after FROM customer_transactions WHERE customer_id=:id ORDER BY id DESC LIMIT 500",{"id":self.party_id}))
        self._tab("المستندات",self._rows("SELECT document_no,title,document_type,file_name,file_path,created_at FROM documents WHERE entity_type=:etype AND entity_id=:id ORDER BY id DESC",{"etype":"supplier" if self.supplier else "customer","id":self.party_id}))

class PartiesWindow(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent); self.setLayoutDirection(Qt.RightToLeft); self.setStyleSheet(APP_STYLE); self.setWindowTitle("العملاء والموردون"); self.setMinimumSize(1150,650); root=QVBoxLayout(self); root.addWidget(QLabel("إدارة العملاء والموردين")); bar=QHBoxLayout(); self.add_customer=QPushButton("إضافة عميل"); self.add_supplier=QPushButton("إضافة مورد"); self.open_btn=QPushButton("فتح البطاقة"); self.refresh_btn=QPushButton("تحديث"); self.add_customer.clicked.connect(lambda:self._add(False)); self.add_supplier.clicked.connect(lambda:self._add(True)); self.open_btn.clicked.connect(self.open_card); self.refresh_btn.clicked.connect(self.load); [bar.addWidget(b) for b in (self.add_customer,self.add_supplier,self.open_btn,self.refresh_btn)]; bar.addStretch(); root.addLayout(bar); sr=QHBoxLayout(); sr.addWidget(QLabel("بحث:")); self.search=QLineEdit(); self.search.setPlaceholderText("الاسم أو الكود أو الهاتف"); self.search.textChanged.connect(self.load); sr.addWidget(self.search,1); root.addLayout(sr); self.tabs=QTabWidget(); self.customers=self._table(); self.suppliers=self._table(); self.tabs.addTab(self.customers,"العملاء"); self.tabs.addTab(self.suppliers,"الموردون"); root.addWidget(self.tabs,1); self.customers.cellDoubleClicked.connect(lambda *_:self.open_card()); self.suppliers.cellDoubleClicked.connect(lambda *_:self.open_card()); self.load()
    def _table(self):
        t=QTableWidget(0,7); t.setHorizontalHeaderLabels(["رقم","الكود","الاسم","النوع","الهاتف","الرصيد","الحالة"]); t.setEditTriggers(QAbstractItemView.NoEditTriggers); t.setSelectionBehavior(QAbstractItemView.SelectRows); t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents); t.horizontalHeader().setStretchLastSection(True); return t
    def load(self):
        q=f"%{self.search.text().strip()}%"; self._load(self.customers,"customers","customer_code",q); self._load(self.suppliers,"suppliers","supplier_code",q)
    def _load(self,tbl,table,code_col,q):
        with get_session() as s:
            cols={r[1] for r in s.connection().exec_driver_sql(f"PRAGMA table_info({table})").fetchall()}; type_expr='"party_type"' if "party_type" in cols else "\'\'"; phone_expr='"phone"' if "phone" in cols else "\'\'"; balance_expr='"current_balance"' if "current_balance" in cols else "0"; active_expr='"is_active"' if "is_active" in cols else "1"; code_expr=f'"{code_col}"' if code_col in cols else "\'\'"; name_expr='"name"' if "name" in cols else "\'\'"; rows=s.execute(text(f'SELECT id,{code_expr} AS code,{name_expr} AS name,{type_expr} AS party_type,{phone_expr} AS phone,{balance_expr} AS current_balance,{active_expr} AS is_active FROM "{table}" WHERE {name_expr} LIKE :q OR {code_expr} LIKE :q OR COALESCE({phone_expr},\'\') LIKE :q ORDER BY id DESC LIMIT 500'),{"q":q}).mappings().all()
        tbl.setRowCount(0)
        for row in rows:
            r=tbl.rowCount(); tbl.insertRow(r)
            for c,v in enumerate(row.values()): tbl.setItem(r,c,QTableWidgetItem("نشط" if c==6 and v else "موقوف" if c==6 else "" if v is None else str(v)))
    def _selected(self): t=self.suppliers if self.tabs.currentIndex()==1 else self.customers; r=t.currentRow(); return t,r
    def open_card(self):
        t,r=self._selected();
        if r<0: QMessageBox.warning(self,"فتح البطاقة","حدد سجلًا أولًا."); return
        PartyCardDialog(int(t.item(r,0).text()),self.tabs.currentIndex()==1,self).exec()
    def _add(self,supplier):
        d=PartyDialog(supplier,parent=self)
        if d.exec()!=QDialog.Accepted:return
        vals=d.values(); table="suppliers" if supplier else "customers"; code_col="supplier_code" if supplier else "customer_code"
        with get_session() as s:
            cols={r[1] for r in s.connection().exec_driver_sql(f"PRAGMA table_info({table})").fetchall()}; payload={code_col:vals["code"],"name":vals["name"],"phone":vals["phone"],"email":vals["email"],"address":vals["address"],"tax_number":vals["tax_number"],"party_type":vals["party_type"],"credit_limit":vals["credit_limit"],"payment_terms":vals["payment_terms"],"currency_code":vals["currency_code"],"is_active":vals["is_active"],"notes":vals["notes"]}; payload={k:v for k,v in payload.items() if k in cols}; s.execute(text(f'INSERT INTO "{table}" ({",".join(payload)}) VALUES ({",".join(":"+k for k in payload)})'),payload); s.commit()
        self.load()
