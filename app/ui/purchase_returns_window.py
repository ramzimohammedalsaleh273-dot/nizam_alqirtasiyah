from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QMessageBox, QInputDialog
)
from sqlalchemy import text
from app.database.connection import get_session
from app.services.purchase_return_service import PurchaseReturnService


class PurchaseReturnsWindow(QWidget):
    """واجهة تشغيلية لمرتجعات المشتريات مع ترحيل المخزون والمحاسبة."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("مرتجعات المشتريات")
        self.setMinimumSize(1050, 650)
        root = QVBoxLayout(self)
        bar = QHBoxLayout()
        for caption, handler in [
            ("تحديث", self.load),
            ("إرجاع الصنف المحدد", self.create_return),
        ]:
            b = QPushButton(caption)
            b.clicked.connect(handler)
            bar.addWidget(b)
        bar.addStretch()
        root.addLayout(bar)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["المعرف", "رقم الفاتورة", "المورد", "التاريخ", "الصنف", "الكمية", "تكلفة الوحدة"]
        )
        root.addWidget(self.table)
        self.load()

    def load(self):
        with get_session() as s:
            rows = s.execute(text("""
                SELECT pi.id, COALESCE(pi.invoice_number, pi.id) AS invoice_number,
                       pi.supplier_id, pi.created_at, pii.product_id,
                       pii.quantity, pii.unit_cost
                FROM purchase_invoices pi
                JOIN purchase_invoice_items pii
                  ON pii.invoice_id = pi.id
                ORDER BY pi.id DESC, pii.id DESC
                LIMIT 300
            """)).fetchall()
        self.table.setRowCount(0)
        for row in rows:
            i = self.table.rowCount()
            self.table.insertRow(i)
            for j, value in enumerate(row):
                self.table.setItem(i, j, QTableWidgetItem(str(value)))

    def create_return(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "تنبيه", "اختر بند مشتريات أولاً.")
            return
        purchase_id = int(self.table.item(row, 0).text())
        product_id = int(self.table.item(row, 4).text())
        available = float(self.table.item(row, 5).text())
        qty, ok = QInputDialog.getDouble(
            self, "مرتجع مشتريات", "كمية الإرجاع:", min(available, 1.0),
            0.01, available, 2
        )
        if not ok:
            return
        method, ok = QInputDialog.getItem(
            self, "طريقة التسوية",
            "طريقة التسوية:",
            ["credit", "cash", "bank_transfer", "card"],
            0, False
        )
        if not ok:
            return
        try:
            result = PurchaseReturnService.create_return(
                purchase_id=purchase_id,
                items=[{"product_id": product_id, "quantity": qty}],
                refund_method=method,
            )
            self.load()
            QMessageBox.information(
                self, "تم",
                f"تم ترحيل المرتجع {result['return_number']} بإجمالي {result['total']:.2f}."
            )
        except Exception as exc:
            QMessageBox.critical(self, "فشل المرتجع", str(exc))
