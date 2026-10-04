from __future__ import annotations

from html import escape
from decimal import Decimal

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
    """معاينة الفاتورة قبل الحفظ مع خيار الحفظ فقط أو الحفظ وإخراج الفاتورة."""

    def __init__(self, cart, payments, total, parent=None):
        super().__init__(parent)
        self.setWindowTitle("مراجعة الفاتورة قبل إتمام البيع")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumSize(900, 650)
        self.print_invoice = False

        root = QVBoxLayout(self)
        title = QLabel("مراجعة فاتورة البيع")
        title.setStyleSheet("font-size:22px;font-weight:700;padding:8px;")
        root.addWidget(title)

        info = QLabel(
            f"عدد الأصناف: {len(cart)}    |    الإجمالي: {Decimal(str(total)):.2f}    |    "
            "لم يتم حفظ البيع حتى تختار أحد أزرار التأكيد."
        )
        root.addWidget(info)

        browser = QTextBrowser()
        browser.setHtml(self._preview_html(cart, payments, total))
        root.addWidget(browser, 1)

        buttons = QHBoxLayout()
        cancel = QPushButton("إلغاء وعدم إتمام البيع")
        no_print = QPushButton("تأكيد البيع بدون طباعة الفاتورة")
        with_print = QPushButton("تأكيد البيع وإخراج الفاتورة")
        cancel.clicked.connect(self.reject)
        no_print.clicked.connect(self._accept_no_print)
        with_print.clicked.connect(self._accept_print)
        buttons.addWidget(cancel)
        buttons.addStretch()
        buttons.addWidget(no_print)
        buttons.addWidget(with_print)
        root.addLayout(buttons)

    def _preview_html(self, cart, payments, total):
        rows = []
        subtotal = Decimal("0")
        for item in cart:
            qty = Decimal(str(item.get("quantity", 0)))
            price = Decimal(str(item.get("unit_price", 0)))
            discount = Decimal(str(item.get("discount", 0)))
            line = qty * price - discount
            subtotal += line
            name = escape(str(item.get("name_ar") or item.get("name") or f"الصنف {item.get('product_id')}"))
            rows.append(
                f"<tr><td>{name}</td><td>{qty}</td><td>{price:.2f}</td>"
                f"<td>{discount:.2f}</td><td>{line:.2f}</td></tr>"
            )
        pay_rows = "".join(
            f"<tr><td>{escape(str(p.get('method') or ''))}</td><td>{Decimal(str(p.get('amount', 0))):.2f}</td></tr>"
            for p in payments
            if Decimal(str(p.get("amount", 0))) > 0
        )
        return f"""
        <html><body dir='rtl' style='font-family:Tahoma;font-size:14px'>
        <h2 style='text-align:center'>فاتورة بيع — معاينة قبل الحفظ</h2>
        <table border='1' cellspacing='0' cellpadding='7' width='100%'>
        <tr><th>الصنف</th><th>الكمية</th><th>سعر الوحدة</th><th>الخصم</th><th>الإجمالي</th></tr>
        {''.join(rows)}
        </table>
        <h3>الإجمالي قبل الضريبة: {subtotal:.2f}</h3>
        <h3>الإجمالي النهائي: {Decimal(str(total)):.2f}</h3>
        <h3>الدفعات</h3>
        <table border='1' cellspacing='0' cellpadding='7'>
        <tr><th>طريقة الدفع</th><th>المبلغ</th></tr>{pay_rows}
        </table>
        </body></html>
        """

    def _accept_no_print(self):
        self.print_invoice = False
        self.accept()

    def _accept_print(self):
        self.print_invoice = True
        self.accept()


class OriginalSaleInvoiceDialog(QDialog):
    """يعرض الفاتورة المحفوظة فعليًا بعد نجاح البيع، مع زر إخراج/طباعة."""

    def __init__(self, sale_id, parent=None, auto_print=False):
        super().__init__(parent)
        self.sale_id = int(sale_id)
        self.setWindowTitle("فاتورة البيع الأصلية")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumSize(850, 650)
        root = QVBoxLayout(self)
        self.browser = QTextBrowser()
        root.addWidget(self.browser, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        print_button = QPushButton("إخراج / طباعة الفاتورة")
        buttons.addButton(print_button, QDialogButtonBox.ActionRole)
        buttons.rejected.connect(self.reject)
        print_button.clicked.connect(self.print_invoice)
        root.addWidget(buttons)
        self.html = self._load_html()
        self.browser.setHtml(self.html)
        if auto_print:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(150, self.print_invoice)

    def _load_html(self):
        with get_session() as s:
            sale = s.execute(
                text("""
                    SELECT s.invoice_number, s.created_at, s.subtotal,
                           s.discount_amount, s.tax_amount, s.total_amount,
                           s.paid_amount, s.due_amount,
                           COALESCE(c.name_ar,c.name,'بدون عميل') AS customer
                    FROM sales s
                    LEFT JOIN customers c ON c.id=s.customer_id
                    WHERE s.id=:id
                    LIMIT 1
                """), {"id": self.sale_id},
            ).mappings().first()
            if not sale:
                raise ValueError("الفاتورة غير موجودة")
            items = s.execute(
                text("""
                    SELECT COALESCE(p.name_ar,p.name,CAST(si.product_id AS TEXT)) AS product_name,
                           si.quantity, si.unit_price, si.discount_amount,
                           si.tax_amount, si.line_total
                    FROM sale_items si
                    LEFT JOIN products p ON p.id=si.product_id
                    WHERE si.sale_id=:id
                    ORDER BY si.id
                """), {"id": self.sale_id},
            ).mappings().all()

        item_rows = "".join(
            f"<tr><td>{escape(str(x['product_name']))}</td>"
            f"<td>{Decimal(str(x['quantity'] or 0))}</td>"
            f"<td>{Decimal(str(x['unit_price'] or 0)):.2f}</td>"
            f"<td>{Decimal(str(x['discount_amount'] or 0)):.2f}</td>"
            f"<td>{Decimal(str(x['tax_amount'] or 0)):.2f}</td>"
            f"<td>{Decimal(str(x['line_total'] or 0)):.2f}</td></tr>"
            for x in items
        )
        return f"""
        <html><body dir='rtl' style='font-family:Tahoma;font-size:14px'>
        <div style='text-align:center'>
          <h1>نظام القرطاسية</h1><h2>فاتورة بيع أصلية</h2>
          <h3>{escape(str(sale['invoice_number']))}</h3>
        </div>
        <table width='100%' cellpadding='6'>
          <tr><td><b>التاريخ:</b> {escape(str(sale['created_at']))}</td>
              <td><b>العميل:</b> {escape(str(sale['customer']))}</td></tr>
        </table>
        <table border='1' cellspacing='0' cellpadding='7' width='100%'>
          <tr><th>الصنف</th><th>الكمية</th><th>سعر الوحدة</th><th>الخصم</th><th>الضريبة</th><th>الإجمالي</th></tr>
          {item_rows}
        </table>
        <table align='left' cellpadding='7'>
          <tr><td>الإجمالي قبل الضريبة</td><td>{Decimal(str(sale['subtotal'] or 0)):.2f}</td></tr>
          <tr><td>الخصم</td><td>{Decimal(str(sale['discount_amount'] or 0)):.2f}</td></tr>
          <tr><td>الضريبة</td><td>{Decimal(str(sale['tax_amount'] or 0)):.2f}</td></tr>
          <tr><td><b>الإجمالي النهائي</b></td><td><b>{Decimal(str(sale['total_amount'] or 0)):.2f}</b></td></tr>
          <tr><td>المدفوع</td><td>{Decimal(str(sale['paid_amount'] or 0)):.2f}</td></tr>
          <tr><td>المتبقي</td><td>{Decimal(str(sale['due_amount'] or 0)):.2f}</td></tr>
        </table>
        </body></html>
        """

    def print_invoice(self):
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() != QDialog.Accepted:
            return
        document = QTextDocument()
        document.setHtml(self.html)
        document.print_(printer)
