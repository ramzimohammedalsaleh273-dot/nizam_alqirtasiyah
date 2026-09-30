from PySide6.QtCore import Qt
from PySide6.QtGui import QTextDocument, QPageSize
from PySide6.QtPrintSupport import QPrinter, QPrintDialog
from PySide6.QtWidgets import (
    QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QPushButton,QTableWidget,
    QTableWidgetItem,QHeaderView,QMessageBox,QDialog,QDialogButtonBox,
    QDoubleSpinBox,QTextEdit,QAbstractItemView,QTabWidget
)
from app.services.sales_invoice_service import SalesInvoiceService
from app.services.sales_return_service import SalesReturnService


def money(value):
    return f"{float(value or 0):,.2f}"


class ReturnDialog(QDialog):
    def __init__(self,data,parent=None):
        super().__init__(parent); self.rows=SalesInvoiceService.returnable_items(data)
        self.setWindowTitle("مرتجع مبيعات — جزئي أو كامل"); self.resize(950,520)
        root=QVBoxLayout(self)
        root.addWidget(QLabel("حدد كمية المرتجع لكل صنف. ترك الكمية صفرًا يعني عدم إرجاع الصنف."))
        self.table=QTableWidget(0,6)
        self.table.setHorizontalHeaderLabels(["الصنف","الأصلي","مرتجع سابقًا","المتاح","كمية المرتجع","السعر"])
        self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        for item in self.rows:
            r=self.table.rowCount(); self.table.insertRow(r)
            for c,v in enumerate([item["name_ar"],item["original_quantity"],item["returned_quantity"],item["available_quantity"],"",money(item["unit_price"])]):
                self.table.setItem(r,c,QTableWidgetItem(str(v)))
            spin=QDoubleSpinBox(); spin.setRange(0,item["available_quantity"]); spin.setDecimals(3); self.table.setCellWidget(r,4,spin)
        root.addWidget(self.table)
        self.reason=QTextEdit(); self.reason.setPlaceholderText("سبب المرتجع (مطلوب)")
        root.addWidget(self.reason)
        buttons=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept); buttons.rejected.connect(self.reject); root.addWidget(buttons)

    def _accept(self):
        if not self.reason.toPlainText().strip():
            QMessageBox.warning(self,"بيانات ناقصة","سبب المرتجع مطلوب."); return
        if not any(self.table.cellWidget(r,4).value()>0 for r in range(self.table.rowCount())):
            QMessageBox.warning(self,"بيانات ناقصة","حدد كمية مرتجع واحدة على الأقل."); return
        self.accept()

    def values(self):
        items=[]
        for r,item in enumerate(self.rows):
            qty=self.table.cellWidget(r,4).value()
            if qty>0: items.append({"product_id":item["product_id"],"quantity":qty})
        return items,self.reason.toPlainText().strip()


class SalesInvoiceWindow(QWidget):
    """ملف فاتورة 360°: تفاصيل، مدفوعات، مرتجعات، تدقيق، وطباعة."""
    def __init__(self,parent=None,sale_id=None):
        super().__init__(parent); self.setWindowTitle("فاتورة البيع — الملف الكامل")
        self.setMinimumSize(1250,800); self.setLayoutDirection(Qt.RightToLeft); self.data=None
        root=QVBoxLayout(self)
        header=QHBoxLayout()
        title=QLabel("فاتورة البيع — الملف الكامل"); title.setStyleSheet("font-size:26px;font-weight:bold")
        self.search=QLineEdit(); self.search.setPlaceholderText("ابحث برقم الفاتورة بالضبط")
        self.search.returnPressed.connect(self.load_by_number)
        find=QPushButton("بحث"); find.clicked.connect(self.load_by_number)
        header.addWidget(title); header.addStretch(); header.addWidget(self.search,1); header.addWidget(find); root.addLayout(header)
        actions=QHBoxLayout()
        for label,slot in [("مرتجع جزئي / كامل",self.create_return),("طباعة الفاتورة",self.print_invoice)]:
            b=QPushButton(label); b.clicked.connect(slot); actions.addWidget(b)
        actions.addStretch(); root.addLayout(actions)
        self.identity=QLabel("ابحث عن رقم الفاتورة لعرضها"); self.identity.setStyleSheet("font-size:20px;font-weight:bold")
        self.meta=QLabel(""); self.meta.setWordWrap(True); root.addWidget(self.identity); root.addWidget(self.meta)
        self.tabs=QTabWidget()
        self.items=self._table(["رمز الصنف","الصنف","الكمية","سعر الوحدة","الخصم","الضريبة","الإجمالي"])
        self.payments=self._table(["طريقة الدفع","المبلغ","التاريخ"])
        self.returns=self._table(["رقم المرتجع","المبلغ","السبب","الحالة","التاريخ"])
        self.history=self._table(["التاريخ","الإجراء"])
        self.tabs.addTab(self.items,"الأصناف"); self.tabs.addTab(self.payments,"المدفوعات")
        self.tabs.addTab(self.returns,"المرتجعات"); self.tabs.addTab(self.history,"السجل والتدقيق")
        root.addWidget(self.tabs,1)
        self.totals=QLabel(""); self.totals.setStyleSheet("font-size:16px;font-weight:bold;padding:12px;border:1px solid #ccd2d8;border-radius:8px")
        root.addWidget(self.totals)
        if sale_id is not None: self.load_sale(sale_id)

    @staticmethod
    def _table(headers):
        t=QTableWidget(0,len(headers)); t.setHorizontalHeaderLabels(headers)
        t.setSelectionBehavior(QAbstractItemView.SelectRows); t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.setAlternatingRowColors(True); t.horizontalHeader().setStretchLastSection(True)
        for i in range(len(headers)-1): t.horizontalHeader().setSectionResizeMode(i,QHeaderView.ResizeToContents)
        return t

    @staticmethod
    def _fill(table,rows):
        table.setRowCount(0)
        for values in rows:
            r=table.rowCount(); table.insertRow(r)
            for c,value in enumerate(values): table.setItem(r,c,QTableWidgetItem("" if value is None else str(value)))

    def load_by_number(self):
        number=self.search.text().strip()
        if not number: return
        data=SalesInvoiceService.find_by_number(number)
        if not data: QMessageBox.warning(self,"غير موجود","لم يتم العثور على فاتورة بهذا الرقم."); return
        self.data=data; self.render()

    def load_sale(self,sale_id):
        data=SalesInvoiceService.get(sale_id)
        if not data: QMessageBox.warning(self,"غير موجود","الفاتورة غير موجودة."); return
        self.data=data; self.search.setText(str(data["sale"].get("invoice_number") or "")); self.render()

    @staticmethod
    def status_ar(value):
        return {"POSTED":"مرحّلة","DRAFT":"مسودة","VOID":"ملغاة","CANCELLED":"ملغاة"}.get(str(value),str(value or ""))

    @staticmethod
    def payment_ar(value):
        return {"CASH":"نقدي","CARD":"بطاقة","TRANSFER":"تحويل","CREDIT":"آجل","credit":"آجل"}.get(str(value),str(value or ""))

    def render(self):
        sale=self.data["sale"]
        self.identity.setText(f"فاتورة رقم: {sale.get('invoice_number','')} — {self.status_ar(sale.get('status'))}")
        self.meta.setText(f"التاريخ: {sale.get('created_at','')}  |  العميل: {sale.get('customer_id') or 'عميل نقدي'}  |  رقم داخلي: {sale.get('id')}")
        self._fill(self.items,[(x.get("sku"),x.get("name_ar"),x.get("quantity"),money(x.get("unit_price")),money(x.get("discount_amount") or x.get("discount")),money(x.get("tax_amount")),money(x.get("line_total"))) for x in self.data["items"]])
        self._fill(self.payments,[(self.payment_ar(x.get("payment_method")),money(x.get("amount")),x.get("created_at")) for x in self.data["payments"]])
        self._fill(self.returns,[(x.get("return_number"),money(x.get("total_amount")),x.get("reason"),self.status_ar(x.get("status")),x.get("created_at")) for x in self.data["returns"]])
        self._fill(self.history,[(x.get("event_date"),x.get("action")) for x in self.data["audit"]])
        sale_total=float(sale.get("total_amount") or 0); returned=sum(float(x.get("total_amount") or 0) for x in self.data["returns"])
        self.totals.setText(f"قبل الضريبة: {money(sale.get('subtotal'))}  |  الخصم: {money(sale.get('discount_amount'))}  |  الضريبة: {money(sale.get('tax_amount'))}  |  الإجمالي: {money(sale_total)}  |  المرتجع: {money(returned)}  |  المدفوع: {money(sale.get('paid_amount'))}  |  المتبقي: {money(sale.get('due_amount'))}")

    def create_return(self):
        if not self.data: return
        dlg=ReturnDialog(self.data,self)
        if dlg.exec()!=QDialog.Accepted: return
        items,reason=dlg.values()
        try:
            result=SalesReturnService.create_return(int(self.data["sale"]["id"]),items,reason)
            QMessageBox.information(self,"تم إنشاء المرتجع",f"رقم المرتجع: {result['return_number']}\nإجمالي المرتجع: {money(result['total'])}")
            self.load_sale(int(self.data["sale"]["id"]))
        except Exception as exc:
            QMessageBox.critical(self,"فشل إنشاء المرتجع",str(exc))

    def print_invoice(self):
        if not self.data: return
        sale=self.data["sale"]; doc=QTextDocument()
        html=[f"<h1 align='center'>فاتورة بيع</h1>",f"<p><b>رقم الفاتورة:</b> {sale.get('invoice_number','')}<br><b>التاريخ:</b> {sale.get('created_at','')}</p>",
              "<table width='100%' border='1' cellspacing='0' cellpadding='6'><tr><th>الصنف</th><th>الكمية</th><th>السعر</th><th>الإجمالي</th></tr>"]
        for x in self.data["items"]: html.append(f"<tr><td>{x.get('name_ar','')}</td><td>{x.get('quantity',0)}</td><td>{money(x.get('unit_price'))}</td><td>{money(x.get('line_total'))}</td></tr>")
        html.append("</table>"); html.append(f"<p><b>الإجمالي:</b> {money(sale.get('total_amount'))}<br><b>المدفوع:</b> {money(sale.get('paid_amount'))}<br><b>المتبقي:</b> {money(sale.get('due_amount'))}</p>")
        doc.setHtml("".join(html))
        printer=QPrinter(QPrinter.HighResolution); printer.setPageSize(QPageSize(QPageSize.A4))
        dialog=QPrintDialog(printer,self)
        if dialog.exec()==QDialog.Accepted: doc.print_(printer)
