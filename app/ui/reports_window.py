from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from sqlalchemy import text
from app.database.connection import get_session


class ReportsWindow(QWidget):
    """تقارير تشغيلية ومالية مبنية مباشرة من البيانات المحفوظة."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("التقارير")
        self.setMinimumSize(1100, 650)

        layout = QVBoxLayout(self)

        title = QLabel("التقارير والتحليلات")
        title.setStyleSheet("font-size:28px;font-weight:bold")
        layout.addWidget(title)

        bar = QHBoxLayout()
        refresh = QPushButton("تحديث التقارير")
        refresh.clicked.connect(self.load)
        bar.addWidget(refresh)
        bar.addStretch()
        layout.addLayout(bar)

        self.summary = QLabel()
        self.summary.setStyleSheet("font-size:17px;padding:10px")
        layout.addWidget(self.summary)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            "التقرير", "عدد العمليات", "القيمة", "المدفوع/الرصيد", "ملاحظات"
        ])
        self.table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.Stretch
        )
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

        self.load()

    def load(self):
        with get_session() as s:
            sales = s.execute(text("""
                SELECT
                    COUNT(*) AS count,
                    COALESCE(SUM(total_amount),0) AS total,
                    COALESCE(SUM(paid_amount),0) AS paid,
                    COALESCE(SUM(due_amount),0) AS due
                FROM sales
                WHERE status='POSTED'
            """)).mappings().one()

            purchases = s.execute(text("""
                SELECT
                    COUNT(*) AS count,
                    COALESCE(SUM(total_amount),0) AS total,
                    COALESCE(SUM(paid_amount),0) AS paid,
                    COALESCE(SUM(due_amount),0) AS due
                FROM purchase_invoices
            """)).mappings().one()

            stock = s.execute(text("""
                SELECT
                    COUNT(*) AS products,
                    COALESCE(SUM(quantity * average_cost),0) AS value
                FROM stock
            """)).mappings().one()

            customers = s.execute(text("""
                SELECT COALESCE(SUM(current_balance),0)
                FROM customers
            """)).scalar() or 0

            suppliers = s.execute(text("""
                SELECT COALESCE(SUM(current_balance),0)
                FROM suppliers
            """)).scalar() or 0

        self.summary.setText(
            f"المبيعات: {float(sales['total']):,.2f}    |    "
            f"المشتريات: {float(purchases['total']):,.2f}    |    "
            f"قيمة المخزون: {float(stock['value']):,.2f}"
        )

        rows = [
            ("المبيعات المرحلة", sales["count"], sales["total"],
             sales["paid"], f"متبقي: {float(sales['due']):,.2f}"),
            ("المشتريات", purchases["count"], purchases["total"],
             purchases["paid"], f"متبقي: {float(purchases['due']):,.2f}"),
            ("المخزون", stock["products"], stock["value"],
             0, "القيمة بالتكلفة المتوسطة"),
            ("أرصدة العملاء", "-", customers, customers,
             "ذمم العملاء الحالية"),
            ("أرصدة الموردين", "-", suppliers, suppliers,
             "ذمم الموردين الحالية"),
        ]

        self.table.setRowCount(0)
        for values in rows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for col, value in enumerate(values):
                self.table.setItem(
                    row, col, QTableWidgetItem(
                        f"{float(value):,.2f}" if isinstance(value, (int, float)) else str(value)
                    )
                )
