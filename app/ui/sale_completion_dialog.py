from __future__ import annotations

from decimal import Decimal
from html import escape

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextDocument
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)
from sqlalchemy import text

from app.database.connection import get_session


class SaleConfirmationDialog(QDialog):
    """معاينة احترافية قبل حفظ البيع، مع حفظ فقط أو حفظ ثم إخراج الفاتورة."""

    def __init__(self, cart, payments, total, parent=None):
        super().__init__(parent)
        self.setWindowTitle("مراجعة فاتورة البيع قبل الإتمام")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumSize(900, 680)
        self.print_invoice = False
        root = QVBoxLayout(self)
        title = QLabel("مراجعة الفاتورة قبل الحفظ")
        title.setStyleSheet("font-size:24px;font-weight:700;padding:8px;")
        root.addWidget(title)
        root.addWidget(QLabel(
            f"عدد الأصناف: {len(cart)}   |   الإجمالي: {Decimal(str(total)):.2f}\n"
            "لم يتم حفظ البيع حتى تختار أحد أزرار التأكيد أدناه."
        ))
        browser = QTextBrowser()
        browser.setStyleSheet("QTextBrowser{background:white;color:#111;border:1px solid #bbb;border-radius:8px;padding:8px;}")
        browser.setHtml(self._preview_html(cart, payments, total))
        root.addWidget(browser, 1)
        buttons = QHBoxLayout()
        cancel = QPushButton("إلغاء والعودة للسلة")
        no_print = QPushButton("تأكيد البيع — بدون طباعة")
        with_print = QPushButton("تأكيد البيع — إخراج الفاتورة")
        cancel.clicked.connect(self.reject)
        no_print.clicked.connect(self._accept_no_print)
        with_print.clicked.connect(self._accept_print)
        buttons.addWidget(cancel)
        buttons.addStretch()
        buttons.addWidget(no_print)
        buttons.addWidget(with_print)
        root.addLayout(buttons)

    def _preview_html(self, cart, payments, total):
        rows, subtotal = [], Decimal("0")
        for item in cart:
            qty = Decimal(str(item.get("quantity", 0)))
            price = Decimal(str(item.get("unit_price", 0)))
            discount = Decimal(str(item.get("discount", item.get("discount_amount", 0)) or 0))
            line = qty * price - discount
            subtotal += line
            name = escape(str(item.get("name_ar") or item.get("name") or f"الصنف {item.get('product_id')}"))
            rows.append(f"<tr><td>{name}</td><td>{qty}</td><td>{price:.2f}</td><td>{discount:.2f}</td><td>{line:.2f}</td></tr>")
        pay_rows = "".join(
            f"<tr><td>{escape(str(p.get('method') or ''))}</td><td>{Decimal(str(p.get('amount', 0))):.2f}</td></tr>"
            for p in payments if Decimal(str(p.get("amount", 0))) > 0
        )
        return f"""
        <html><body dir='rtl' style='font-family:Tahoma,Arial;font-size:14px;background:#fff;color:#111'>
        <div style='max-width:760px;margin:auto'>
          <div style='text-align:center;border-bottom:2px solid #111;padding-bottom:10px'>
            <h1 style='margin:4px'>نظام القرطاسية</h1>
            <div>فاتورة بيع — معاينة قبل الحفظ</div>
          </div>
          <table border='1' cellspacing='0' cellpadding='7' width='100%' style='margin-top:12px;border-collapse:collapse'>
            <tr><th>الصنف</th><th>الكمية</th><th>سعر الوحدة</th><th>الخصم</th><th>الإجمالي</th></tr>{''.join(rows)}
          </table>
          <div style='text-align:left;margin-top:12px'><b>الإجمالي قبل الضريبة: {subtotal:.2f}</b><br><b>الإجمالي النهائي: {Decimal(str(total)):.2f}</b></div>
          <h3>الدفعات</h3>
          <table border='1' cellspacing='0' cellpadding='7' style='border-collapse:collapse'>{pay_rows}</table>
        </div></body></html>
        """

    def _accept_no_print(self):
        self.print_invoice = False
        self.accept()

    def _accept_print(self):
        self.print_invoice = True
        self.accept()


class OriginalSaleInvoiceDialog(QDialog):
    """فاتورة أصلية محفوظة، بتصميم إيصال متجر/سوبرماركت مع خيار الطباعة أو الإخراج."""

    def __init__(self, sale_id, parent=None, auto_print=False):
        super().__init__(parent)
        self.sale_id = int(sale_id)
        self.setWindowTitle("الفاتورة الأصلية — فاتورة بيع")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumSize(900, 720)
        root = QVBoxLayout(self)
        title = QLabel("الفاتورة الأصلية المحفوظة")
        title.setStyleSheet("font-size:22px;font-weight:700;padding:6px;")
        root.addWidget(title)
        self.browser = QTextBrowser()
        self.browser.setStyleSheet("QTextBrowser{background:#f7f7f7;border:1px solid #aaa;border-radius:8px;}")
        root.addWidget(self.browser, 1)
        buttons = QHBoxLayout()
        back = QPushButton("رجوع")
        print_button = QPushButton("إخراج / طباعة الفاتورة")
        back.clicked.connect(self.reject)
        print_button.clicked.connect(self.print_invoice)
        buttons.addWidget(back)
        buttons.addStretch()
        buttons.addWidget(print_button)
        root.addLayout(buttons)
        try:
            self.html = self._load_html()
            self.browser.setHtml(self.html)
        except Exception as exc:
            self.html = ""
            QMessageBox.critical(self, "تعذر عرض الفاتورة", str(exc))
        if auto_print:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(250, self.print_invoice)

    @staticmethod
    def _table_columns(conn, table):
        return {row[1] for row in conn.exec_driver_sql(f'PRAGMA table_info("{table}")').fetchall()}

    def _load_html(self):
        with get_session() as s:
            conn = s.connection()
            customer_cols = self._table_columns(conn, "customers")
            if "name_ar" in customer_cols and "name" in customer_cols:
                customer_expr = "COALESCE(c.name_ar,c.name,'بدون عميل')"
            elif "name_ar" in customer_cols:
                customer_expr = "COALESCE(c.name_ar,'بدون عميل')"
            elif "name" in customer_cols:
                customer_expr = "COALESCE(c.name,'بدون عميل')"
            else:
                customer_expr = "'بدون عميل'"

            sale = s.execute(text(f"""
                SELECT s.invoice_number, s.created_at, s.subtotal,
                       s.discount_amount, s.tax_amount, s.total_amount,
                       s.paid_amount, s.due_amount,
                       {customer_expr} AS customer
                FROM sales s
                LEFT JOIN customers c ON c.id=s.customer_id
                WHERE s.id=:id LIMIT 1
            """), {"id": self.sale_id}).mappings().first()
            if not sale:
                raise ValueError("الفاتورة غير موجودة")

            product_cols = self._table_columns(conn, "products")
            if "name_ar" in product_cols and "name" in product_cols:
                product_expr = "COALESCE(p.name_ar,p.name,CAST(si.product_id AS TEXT))"
            elif "name_ar" in product_cols:
                product_expr = "COALESCE(p.name_ar,CAST(si.product_id AS TEXT))"
            elif "name" in product_cols:
                product_expr = "COALESCE(p.name,CAST(si.product_id AS TEXT))"
            else:
                product_expr = "CAST(si.product_id AS TEXT)"

            items = s.execute(text(f"""
                SELECT {product_expr} AS product_name,
                       si.quantity, si.unit_price, si.discount_amount,
                       si.tax_amount, si.line_total
                FROM sale_items si
                LEFT JOIN products p ON p.id=si.product_id
                WHERE si.sale_id=:id ORDER BY si.id
            """), {"id": self.sale_id}).mappings().all()

        item_rows = "".join(
            f"<tr><td>{escape(str(x['product_name']))}</td>"
            f"<td>{Decimal(str(x['quantity'] or 0))}</td>"
            f"<td>{Decimal(str(x['unit_price'] or 0)):.2f}</td>"
            f"<td>{Decimal(str(x['discount_amount'] or 0)):.2f}</td>"
            f"<td>{Decimal(str(x['tax_amount'] or 0)):.2f}</td>"
            f"<td>{Decimal(str(x['line_total'] or 0)):.2f}</td></tr>"
            for x in items
        )
        total = Decimal(str(sale['total_amount'] or 0))
        tax = Decimal(str(sale['tax_amount'] or 0))
        paid = Decimal(str(sale['paid_amount'] or 0))
        due = Decimal(str(sale['due_amount'] or 0))
        return f"""
        <html><head><style>
        body{{font-family:Tahoma,Arial;color:#111;background:#eee;margin:0;padding:18px;}}
        .receipt{{background:#fff;max-width:760px;margin:auto;padding:28px;border:1px solid #bbb;box-shadow:0 2px 10px #bbb;}}
        .center{{text-align:center}} .line{{border-top:1px dashed #444;margin:12px 0}}
        table{{width:100%;border-collapse:collapse}} th,td{{padding:8px;border-bottom:1px solid #ddd;text-align:right}}
        th{{background:#f0f0f0}} .totals{{width:55%;margin-right:auto;margin-top:15px}} .grand{{font-size:20px;font-weight:bold;border-top:2px solid #111}}
        .meta td{{border:0;padding:3px 8px}} .small{{font-size:12px;color:#555}}
        </style></head><body dir='rtl'>
        <div class='receipt'>
          <div class='center'><h1 style='margin:0'>نظام القرطاسية</h1><h2 style='margin:6px'>فاتورة بيع أصلية</h2><div class='small'>هذه الفاتورة محفوظة في النظام</div></div>
          <div class='line'></div>
          <table class='meta'><tr><td><b>رقم الفاتورة:</b> {escape(str(sale['invoice_number']))}</td><td><b>التاريخ:</b> {escape(str(sale['created_at']))}</td></tr><tr><td><b>العميل:</b> {escape(str(sale['customer']))}</td><td><b>حالة الدفع:</b> {'مدفوعة بالكامل' if due <= 0 else 'متبقي'}</td></tr></table>
          <div class='line'></div>
          <table><tr><th>الصنف</th><th>الكمية</th><th>السعر</th><th>الخصم</th><th>الضريبة</th><th>الإجمالي</th></tr>{item_rows}</table>
          <table class='totals'><tr><td>الإجمالي قبل الضريبة</td><td>{Decimal(str(sale['subtotal'] or 0)):.2f}</td></tr><tr><td>الخصم</td><td>{Decimal(str(sale['discount_amount'] or 0)):.2f}</td></tr><tr><td>الضريبة</td><td>{tax:.2f}</td></tr><tr class='grand'><td>الإجمالي النهائي</td><td>{total:.2f}</td></tr><tr><td>المدفوع</td><td>{paid:.2f}</td></tr><tr><td>المتبقي</td><td>{due:.2f}</td></tr></table>
          <div class='line'></div><div class='center small'>شكرًا لتعاملكم معنا — نظام القرطاسية</div>
        </div></body></html>
        """

    def print_invoice(self):
        if not self.html:
            return
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() != QDialog.Accepted:
            return
        document = QTextDocument()
        document.setHtml(self.html)
        document.print_(printer)
