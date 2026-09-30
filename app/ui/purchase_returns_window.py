from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QMessageBox, QInputDialog, QHeaderView
)
from sqlalchemy import text
from app.database.connection import get_session
from app.services.purchase_return_service import PurchaseReturnService


class PurchaseReturnsWindow(QWidget):
    """واجهة تشغيلية لمرتجعات المشتريات مع عرض الكميات القابلة للإرجاع."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("مرتجعات المشتريات")
        self.setMinimumSize(1150, 680)
        self.setLayoutDirection(2)

        root = QVBoxLayout(self)
        bar = QHBoxLayout()
        refresh = QPushButton("تحديث")
        refresh.clicked.connect(self.load)
        create = QPushButton("إرجاع الصنف المحدد")
        create.clicked.connect(self.create_return)
        bar.addWidget(refresh)
        bar.addWidget(create)
        bar.addStretch()
        root.addLayout(bar)

        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels([
            "المعرف", "رقم الفاتورة", "المورد", "التاريخ",
            "الصنف", "الكمية الأصلية", "مرتجع سابق", "المتاح للإرجاع", "تكلفة الوحدة"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        root.addWidget(self.table)

        self.status = QTableWidgetItem
        self.load()

    def _columns(self, session, table):
        return {r[1] for r in session.connection().exec_driver_sql(
            f"PRAGMA table_info({table})"
        ).fetchall()}

    def load(self):
        try:
            with get_session() as s:
                pic = self._columns(s, "purchase_invoices")
                iic = self._columns(s, "purchase_invoice_items")
                if "id" not in pic or "id" not in iic:
                    raise ValueError("بنية فواتير المشتريات غير صالحة")
                fk = "invoice_id" if "invoice_id" in iic else (
                    "purchase_invoice_id" if "purchase_invoice_id" in iic else None
                )
                if not fk:
                    raise ValueError("جدول بنود المشتريات لا يحتوي مفتاح الفاتورة")

                date_expr = "pi.created_at" if "created_at" in pic else (
                    "pi.invoice_date" if "invoice_date" in pic else "CURRENT_TIMESTAMP"
                )
                supplier_join = "LEFT JOIN suppliers s ON s.id=pi.supplier_id" if "supplier_id" in pic else ""
                supplier_expr = "COALESCE(s.name, pi.supplier_id, '')" if "supplier_id" in pic else "''"

                rows = s.execute(text(f"""
                    SELECT pi.id,
                           COALESCE(pi.invoice_number, pi.id) AS invoice_number,
                           {supplier_expr} AS supplier_name,
                           {date_expr} AS invoice_date,
                           pii.product_id,
                           COALESCE(p.name_ar, pii.product_id) AS product_name,
                           pii.quantity,
                           COALESCE((
                               SELECT SUM(pri.quantity)
                               FROM purchase_return_items pri
                               JOIN purchase_returns pr ON pr.id=pri.return_id
                               WHERE pr.purchase_id=pi.id
                                 AND pri.product_id=pii.product_id
                                 AND pr.status <> 'VOID'
                           ),0) AS returned_quantity,
                           pii.unit_cost
                    FROM purchase_invoices pi
                    JOIN purchase_invoice_items pii ON pii.{fk}=pi.id
                    LEFT JOIN products p ON p.id=pii.product_id
                    {supplier_join}
                    ORDER BY pi.id DESC, pii.id DESC
                    LIMIT 500
                """)).fetchall()

            self.table.setRowCount(0)
            visible = 0
            for row in rows:
                original = float(row.quantity or 0)
                returned = float(row.returned_quantity or 0)
                available = max(0.0, original - returned)
                if available <= 0:
                    continue
                values = [
                    row.id, row.invoice_number, row.supplier_name, row.invoice_date,
                    row.product_name, original, returned, available, row.unit_cost
                ]
                r = self.table.rowCount()
                self.table.insertRow(r)
                for c, value in enumerate(values):
                    item = QTableWidgetItem("" if value is None else str(value))
                    if c == 4:
                        item.setData(32, int(row.product_id))
                    self.table.setItem(r, c, item)
                visible += 1

            self.setWindowTitle(f"مرتجعات المشتريات — {visible} بند قابل للإرجاع")
        except Exception as exc:
            self.table.setRowCount(0)
            QMessageBox.critical(self, "تعذر فتح مرتجعات المشتريات", str(exc))

    def create_return(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "تنبيه", "اختر بند مشتريات أولاً.")
            return

        purchase_id = int(self.table.item(row, 0).text())
        product_id = int(self.table.item(row, 4).data(0) or 0) if self.table.item(row, 4) else 0
        # اسم المنتج ظاهر في العمود 4، والمعرف الحقيقي محفوظ في UserRole.
        product_id_item = self.table.item(row, 4)
        if product_id_item is not None:
            product_id = int(product_id_item.data(32) or 0)
        if not product_id:
            QMessageBox.critical(self, "خطأ", "تعذر تحديد الصنف المحدد.")
            return

        available = float(self.table.item(row, 7).text())
        qty, ok = QInputDialog.getDouble(
            self, "مرتجع مشتريات", "كمية الإرجاع:", min(available, 1.0),
            0.01, available, 2
        )
        if not ok:
            return

        method, ok = QInputDialog.getItem(
            self, "طريقة التسوية", "طريقة التسوية:",
            ["credit", "cash", "bank_transfer", "card"], 0, False
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
