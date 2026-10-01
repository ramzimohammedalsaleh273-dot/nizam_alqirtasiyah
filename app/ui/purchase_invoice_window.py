from PySide6.QtCore import Qt
from PySide6.QtGui import QTextDocument
from PySide6.QtPrintSupport import QPrinter, QPrintDialog
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox,
    QTabWidget, QGridLayout, QFrame
)
from sqlalchemy import text

from app.database.connection import get_session
from app.services.purchase_service import PurchaseService
from app.ui.theme import APP_STYLE


def money(v):
    return f"{float(v or 0):,.2f}"


class PurchaseInvoiceWindow(QWidget):
    """ملف فاتورة شراء كامل وفق نموذج الرأس + التفاصيل والتبويبات المرجعية."""

    def __init__(self, parent=None, invoice_id=None):
        super().__init__(parent)
        self.setWindowTitle("فاتورة الشراء — الملف الكامل")
        self.setMinimumSize(1280, 820)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setStyleSheet(APP_STYLE)
        self.data = None

        root = QVBoxLayout(self)
        head = QHBoxLayout()
        title = QLabel("ملف فاتورة الشراء")
        title.setObjectName("SectionTitle")
        head.addWidget(title)
        head.addStretch()
        self.search = QLineEdit()
        self.search.setPlaceholderText("أدخل رقم فاتورة الشراء ثم Enter")
        self.search.returnPressed.connect(self.load_by_number)
        head.addWidget(self.search)
        open_button = QPushButton("فتح")
        open_button.clicked.connect(self.load_by_number)
        head.addWidget(open_button)
        print_button = QPushButton("طباعة")
        print_button.clicked.connect(self.print_invoice)
        head.addWidget(print_button)
        root.addLayout(head)

        self.identity = QLabel("أدخل رقم الفاتورة لعرض الملف الكامل")
        self.identity.setStyleSheet("font-size:21px;font-weight:700;")
        root.addWidget(self.identity)
        self.meta = QLabel("")
        self.meta.setWordWrap(True)
        root.addWidget(self.meta)

        self.tabs = QTabWidget()
        self.items = self._table(["الكود","الصنف","الكمية","تكلفة الوحدة","الإجمالي"])
        self.payments = self._table(["التاريخ","طريقة الدفع","المبلغ","المرجع"])
        self.tax = self._table(["البند","القيمة"])
        self.accounting = self._table(["رقم القيد","التاريخ","الحساب","مدين","دائن","الحالة"])
        self.documents = self._table(["رقم المستند","العنوان","النوع","الملف","التاريخ"])
        self.returns = self._table(["رقم المرتجع","المبلغ","السبب","الحالة","التاريخ"])
        self.history = self._table(["التاريخ","الإجراء"])
        for widget, caption in [
            (self.items,"الأصناف"),(self.payments,"الدفع"),(self.tax,"الضريبة"),
            (self.accounting,"المحاسبة"),(self.documents,"المستندات"),
            (self.returns,"المرتجعات"),(self.history,"سجل التعديلات")
        ]:
            self.tabs.addTab(widget, caption)
        root.addWidget(self.tabs, 1)

        metrics = QGridLayout()
        self.metric_labels = {}
        for i,(key,label) in enumerate([
            ("subtotal","قبل الضريبة"),("tax","الضريبة"),("total","الإجمالي"),
            ("paid","المدفوع"),("due","المتبقي")
        ]):
            card=QFrame(); card.setObjectName("Card"); lay=QVBoxLayout(card)
            lay.addWidget(QLabel(label))
            value=QLabel("0.00"); value.setStyleSheet("font-size:18px;font-weight:700;")
            lay.addWidget(value); self.metric_labels[key]=value
            metrics.addWidget(card,i//3,i%3)
        root.addLayout(metrics)

        if invoice_id is not None:
            self.load_invoice(invoice_id)

    @staticmethod
    def _table(headers):
        t=QTableWidget(0,len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.setSelectionBehavior(QAbstractItemView.SelectRows)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.setAlternatingRowColors(True)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        t.horizontalHeader().setStretchLastSection(True)
        return t

    @staticmethod
    def _fill(table, rows):
        table.setRowCount(0)
        for values in rows:
            r=table.rowCount(); table.insertRow(r)
            for c,v in enumerate(values):
                table.setItem(r,c,QTableWidgetItem("" if v is None else str(v)))

    def load_by_number(self):
        number=self.search.text().strip()
        if not number:return
        with get_session() as s:
            row=s.execute(text("""
                SELECT id FROM purchase_invoices WHERE invoice_number=:n LIMIT 1
            """),{"n":number}).scalar()
        if row is None:
            QMessageBox.warning(self,"غير موجود","لم يتم العثور على فاتورة شراء بهذا الرقم.")
            return
        self.load_invoice(int(row))

    def load_invoice(self, invoice_id):
        data=PurchaseService.get_purchase(int(invoice_id))
        if not data:
            QMessageBox.warning(self,"غير موجود","فاتورة الشراء غير موجودة.")
            return
        with get_session() as s:
            journal=s.execute(text("""
                SELECT je.entry_number,je.entry_date,a.account_name,jl.debit,jl.credit,je.status
                FROM journal_entries je
                LEFT JOIN journal_entry_lines jl ON jl.journal_entry_id=je.id
                LEFT JOIN accounts a ON a.id=jl.account_id
                WHERE je.source_type='PURCHASE' AND je.source_id=:id
                ORDER BY je.id DESC,jl.id
            """),{"id":invoice_id}).all()
            docs=s.execute(text("""
                SELECT document_no,title,document_type,file_name,file_path,created_at
                FROM documents WHERE entity_id=:id AND entity_type IN ('purchase','purchase_invoice')
                ORDER BY id DESC
            """),{"id":invoice_id}).all()
            pays=s.execute(text("""
                SELECT payment_date,payment_method,amount,reference_number
                FROM cash_payments WHERE supplier_id=:supplier ORDER BY id DESC LIMIT 200
            """),{"supplier":data.get("supplier_id")}).all()
            returns=s.execute(text("""
                SELECT return_number,total_amount,reason,status,created_at
                FROM purchase_returns WHERE supplier_id=:supplier ORDER BY id DESC LIMIT 200
            """),{"supplier":data.get("supplier_id")}).all()
            audit=s.execute(text("""
                SELECT created_at,action FROM audit_logs
                WHERE entity_id=:id AND entity_type IN ('purchase','purchase_invoice')
                ORDER BY rowid DESC LIMIT 100
            """),{"id":invoice_id}).all()

        self.data=data
        self.search.setText(str(data.get("invoice_number") or ""))
        self.identity.setText(f"فاتورة شراء رقم: {data.get('invoice_number','')} — الحالة: {data.get('status','')}")
        self.meta.setText(f"التاريخ: {data.get('invoice_date','')} | المورد: {data.get('supplier_id','—')} | المستودع: {data.get('warehouse_id','—')}")

        self._fill(self.items,[(x.get("sku"),x.get("name_ar"),x.get("quantity"),money(x.get("unit_cost")),money(x.get("line_total") or float(x.get("quantity") or 0)*float(x.get("unit_cost") or 0))) for x in data.get("items",[])])
        self._fill(self.payments,[tuple(x) for x in pays])
        self._fill(self.tax,[("قبل الضريبة",money(data.get("subtotal"))),("الضريبة",money(data.get("tax_amount"))),("الإجمالي",money(data.get("total_amount")))])
        self._fill(self.accounting,[tuple(x) for x in journal])
        self._fill(self.documents,[tuple(x) for x in docs])
        self._fill(self.returns,[tuple(x) for x in returns])
        self._fill(self.history,[tuple(x) for x in audit])
        for k,v in [("subtotal",data.get("subtotal")),("tax",data.get("tax_amount")),("total",data.get("total_amount")),("paid",data.get("paid_amount")),("due",data.get("due_amount"))]:
            self.metric_labels[k].setText(money(v))

    def print_invoice(self):
        if not self.data:return
        doc=QTextDocument()
        html=[f"<h1 align='center'>فاتورة شراء</h1><p>رقم: {self.data.get('invoice_number','')}<br>التاريخ: {self.data.get('invoice_date','')}</p>",
              "<table width='100%' border='1' cellspacing='0' cellpadding='6'><tr><th>الصنف</th><th>الكمية</th><th>التكلفة</th><th>الإجمالي</th></tr>"]
        for x in self.data.get("items",[]):
            html.append(f"<tr><td>{x.get('name_ar','')}</td><td>{x.get('quantity',0)}</td><td>{money(x.get('unit_cost'))}</td><td>{money(x.get('line_total'))}</td></tr>")
        html.append(f"</table><p>الإجمالي: {money(self.data.get('total_amount'))}<br>المدفوع: {money(self.data.get('paid_amount'))}<br>المتبقي: {money(self.data.get('due_amount'))}</p>")
        doc.setHtml("".join(html))
        printer=QPrinter(QPrinter.HighResolution)
        dialog=QPrintDialog(printer,self)
        if dialog.exec():
            doc.print_(printer)
