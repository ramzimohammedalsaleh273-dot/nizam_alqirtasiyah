from app.ui.theme import APP_STYLE
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QTableWidget,QTableWidgetItem,QPushButton,QMessageBox,QInputDialog
from sqlalchemy import text
from app.database.connection import get_session
from app.services.sales_return_service import SalesReturnService


class SalesReturnsWindow(QWidget):
    """واجهة تشغيلية لمرتجعات المبيعات."""
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setStyleSheet(APP_STYLE)
        self.setStyleSheet(APP_STYLE)
        self.setWindowTitle("مرتجعات المبيعات")
        self.setMinimumSize(1100,650)
        root=QVBoxLayout(self)
        bar=QHBoxLayout()
        for caption,handler in [("تحديث",self.load),("إرجاع الصنف المحدد",self.create_return)]:
            b=QPushButton(caption); b.clicked.connect(handler); bar.addWidget(b)
        bar.addStretch(); root.addLayout(bar)
        self.table=QTableWidget(0,7)
        self.table.setHorizontalHeaderLabels(["المعرف","الفاتورة","العميل","التاريخ","الصنف","الكمية","السعر"])
        root.addWidget(self.table)
        self.load()

    def load(self):
        with get_session() as s:
            cols={r[1] for r in s.execute(text("PRAGMA table_info(sale_items)")).fetchall()}
            discount="COALESCE(si.discount_amount,si.discount,0)" if "discount" in cols else "COALESCE(si.discount_amount,0)"
            rows=s.execute(text(f"""
                SELECT sl.id,COALESCE(sl.invoice_number,sl.id),sl.customer_id,sl.created_at,
                       si.product_id,si.quantity,si.unit_price
                FROM sales sl JOIN sale_items si ON si.sale_id=sl.id
                WHERE COALESCE(sl.status,'POSTED') NOT IN ('VOID','CANCELLED')
                ORDER BY sl.id DESC,si.id DESC LIMIT 300
            """)).fetchall()
        self.table.setRowCount(0)
        for r in rows:
            i=self.table.rowCount(); self.table.insertRow(i)
            for j,v in enumerate(r): self.table.setItem(i,j,QTableWidgetItem(str(v)))

    def create_return(self):
        row=self.table.currentRow()
        if row<0:
            QMessageBox.warning(self,"تنبيه","اختر بند بيع أولاً."); return
        sale_id=int(self.table.item(row,0).text())
        product_id=int(self.table.item(row,4).text())
        sold=float(self.table.item(row,5).text())
        qty,ok=QInputDialog.getDouble(self,"مرتجع مبيعات","كمية الإرجاع:",min(sold,1.0),0.01,sold,2)
        if not ok:return
        reason,ok=QInputDialog.getText(self,"سبب المرتجع","السبب:","")
        if not ok or not reason.strip():return
        try:
            result=SalesReturnService.create_return(sale_id,[{"product_id":product_id,"quantity":qty}],reason)
            self.load()
            QMessageBox.information(self,"تم",f"تم ترحيل المرتجع {result['return_number']} بإجمالي {result['total']:.2f}.")
        except Exception as e:
            QMessageBox.critical(self,"فشل المرتجع",str(e))

# UI reference theme is applied by the main application shell.
