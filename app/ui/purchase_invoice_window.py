from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLineEdit,QPushButton,QLabel,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QMessageBox,QTabWidget
from app.services.purchase_service import PurchaseService
from app.ui.theme import APP_STYLE

class PurchaseInvoiceWindow(QWidget):
    def __init__(self,parent=None,invoice_id=None):
        super().__init__(parent);self.setWindowTitle('ملف فاتورة الشراء');self.setMinimumSize(1200,760);self.setLayoutDirection(Qt.RightToLeft);self.setStyleSheet(APP_STYLE);self.data=None;root=QVBoxLayout(self);h=QHBoxLayout();self.search=QLineEdit();self.search.setPlaceholderText('رقم فاتورة الشراء');b=QPushButton('فتح');b.clicked.connect(self.load_by_number);h.addWidget(self.search,1);h.addWidget(b);root.addLayout(h);self.title=QLabel('ملف فاتورة الشراء');self.title.setStyleSheet('font-size:26px;font-weight:700');root.addWidget(self.title);self.tabs=QTabWidget();root.addWidget(self.tabs,1)
        if invoice_id is not None:self.load_invoice(invoice_id)
    def load_by_number(self):
        n=self.search.text().strip()
        if not n:return
        try:
            rows=PurchaseService.list_purchases();r=next((x for x in rows if str(x.get('invoice_number'))==n),None)
            if not r:return QMessageBox.warning(self,'غير موجود','لم يتم العثور على فاتورة الشراء.')
            self.load_invoice(int(r['id']))
        except Exception as e:QMessageBox.critical(self,'فشل الفتح',str(e))
    def tab(self,title,headers,rows):
        t=QTableWidget(0,len(headers));t.setHorizontalHeaderLabels(headers);t.setSelectionBehavior(QAbstractItemView.SelectRows);t.setEditTriggers(QAbstractItemView.NoEditTriggers);t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents);t.horizontalHeader().setStretchLastSection(True)
        for row in rows:
            rr=t.rowCount();t.insertRow(rr)
            for c,v in enumerate(row):t.setItem(rr,c,QTableWidgetItem('' if v is None else str(v)))
        self.tabs.addTab(t,title)
    def load_invoice(self,invoice_id):
        try:data=PurchaseService.get_purchase(int(invoice_id))
        except Exception as e:return QMessageBox.critical(self,'فشل فتح الفاتورة',str(e))
        if not data:return QMessageBox.warning(self,'غير موجود','الفاتورة غير موجودة.')
        self.data=data;self.search.setText(str(data.get('invoice_number') or ''));self.title.setText(f"فاتورة شراء: {data.get('invoice_number','')}");self.tabs.clear();items=data.get('items',[]);self.tab('الأصناف',['رمز الصنف','الصنف','الكمية','تكلفة الوحدة','الإجمالي'],[(x.get('sku'),x.get('name_ar'),x.get('quantity'),x.get('unit_cost'),x.get('line_total')) for x in items]);self.tab('الملخص',['البند','القيمة'],[('المورد',data.get('supplier_id')),('التاريخ',data.get('invoice_date')),('قبل الضريبة',data.get('subtotal')),('الضريبة',data.get('tax_amount')),('الإجمالي',data.get('total_amount')),('المدفوع',data.get('paid_amount')),('المتبقي',data.get('due_amount')),('الحالة',data.get('status'))])
