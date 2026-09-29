from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from sqlalchemy import text
from app.services.document_number_service import DocumentNumberService


class AccountingService:

    TAX_RATE = Decimal("0.15")

    PAYMENT_ACCOUNTS = {
        "cash": "1100",
        "card": "1200",
        "bank": "1200",
        "bank_transfer": "1200",
    }

    @staticmethod
    def money(value):
        return Decimal(str(value)).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

    @staticmethod
    def get_account_id(session, code):
        row = session.execute(
            text("""
                SELECT id
                FROM accounts
                WHERE account_code=:code
                  AND is_active=1
                  AND allow_posting=1
                LIMIT 1
            """),
            {"code": code}
        ).fetchone()

        if not row:
            raise ValueError(f"الحساب المحاسبي غير موجود أو غير قابل للترحيل: {code}")

        return int(row[0])

    @staticmethod
    def next_entry_number(session):
        return DocumentNumberService.next_number(
            session,
            document_type="JOURNAL",
            prefix="JE",
            width=6,
        )

    @classmethod
    def post_sale(
        cls,
        session,
        sale_id,
        invoice_number,
        subtotal,
        tax_amount,
        total_amount,
        paid_amount,
        due_amount,
        payment_method,
        cost_of_goods_sold,
        payments=None,
        customer_id=None,
    ):
        subtotal = cls.money(subtotal)
        tax_amount = cls.money(tax_amount)
        total_amount = cls.money(total_amount)
        paid_amount = cls.money(paid_amount)
        due_amount = cls.money(due_amount)
        cost_of_goods_sold = cls.money(cost_of_goods_sold)

        # حسابات أساسية
        sales_account = cls.get_account_id(session, "4100")
        vat_output_account = cls.get_account_id(session, "2200")
        cogs_account = cls.get_account_id(session, "5100")
        inventory_account = cls.get_account_id(session, "1400")

        lines = []

        # المدين: توزيع التحصيل على جميع طرق الدفع.
        # هذا يسمح مثلًا بـ 100 نقدًا + 200 بطاقة + 50 تحويل + 50 آجل.
        if payments is None:
            if paid_amount > 0:
                payments = [{"method": payment_method, "amount": paid_amount}]
            else:
                payments = []

        for payment in payments:
            method = payment["method"]
            amount = cls.money(payment["amount"])
            if method == "credit" or amount <= 0:
                continue
            if method not in cls.PAYMENT_ACCOUNTS:
                raise ValueError(f"طريقة الدفع غير مدعومة محاسبيًا: {method}")
            debit_account = cls.get_account_id(session, cls.PAYMENT_ACCOUNTS[method])
            lines.append({
                "account_id": debit_account,
                "debit": amount,
                "credit": Decimal("0"),
                "description": f"تحصيل {method} لفاتورة {invoice_number}",
            })

        # البيع الآجل
        if due_amount > 0:
            if not customer_id:
                raise ValueError(
                    "لا يمكن تسجيل مبلغ آجل بدون عميل"
                )

            customer_account = cls.get_account_id(
                session,
                "1300"
            )

            lines.append({
                "account_id": customer_account,
                "debit": due_amount,
                "credit": Decimal("0"),
                "description": f"ذمم العميل لفاتورة {invoice_number}",
            })

        # الإيراد
        if subtotal > 0:
            lines.append({
                "account_id": sales_account,
                "debit": Decimal("0"),
                "credit": subtotal,
                "description": f"إيراد فاتورة {invoice_number}",
            })

        # ضريبة المخرجات
        if tax_amount > 0:
            lines.append({
                "account_id": vat_output_account,
                "debit": Decimal("0"),
                "credit": tax_amount,
                "description": f"ضريبة مخرجات فاتورة {invoice_number}",
            })

        # تكلفة البضاعة
        if cost_of_goods_sold > 0:
            lines.append({
                "account_id": cogs_account,
                "debit": cost_of_goods_sold,
                "credit": Decimal("0"),
                "description": f"تكلفة بضاعة فاتورة {invoice_number}",
            })

            lines.append({
                "account_id": inventory_account,
                "debit": Decimal("0"),
                "credit": cost_of_goods_sold,
                "description": f"تخفيض مخزون فاتورة {invoice_number}",
            })

        debit_total = sum(
            (x["debit"] for x in lines),
            Decimal("0")
        )

        credit_total = sum(
            (x["credit"] for x in lines),
            Decimal("0")
        )

        debit_total = cls.money(debit_total)
        credit_total = cls.money(credit_total)

        if debit_total != credit_total:
            raise ValueError(
                f"القيد غير متوازن: مدين={debit_total} دائن={credit_total}"
            )

        entry_number = cls.next_entry_number(session)

        session.execute(
            text("""
                INSERT INTO journal_entries
                (
                    entry_number,
                    entry_date,
                    description,
                    source_type,
                    source_id,
                    status,
                    fiscal_period_id,
                    created_by,
                    created_at
                )
                VALUES
                (
                    :entry_number,
                    :entry_date,
                    :description,
                    'SALE',
                    :source_id,
                    'POSTED',
                    NULL,
                    NULL,
                    CURRENT_TIMESTAMP
                )
            """),
            {
                "entry_number": entry_number,
                "entry_date": datetime.now().strftime("%Y-%m-%d"),
                "description": f"ترحيل فاتورة بيع {invoice_number}",
                "source_id": sale_id,
            }
        )

        entry_id = session.execute(
            text("SELECT last_insert_rowid()")
        ).scalar()

        for line in lines:
            session.execute(
                text("""
                    INSERT INTO journal_entry_lines
                    (
                        journal_entry_id,
                        account_id,
                        cost_center_id,
                        description,
                        debit,
                        credit
                    )
                    VALUES
                    (
                        :entry_id,
                        :account_id,
                        NULL,
                        :description,
                        :debit,
                        :credit
                    )
                """),
                {
                    "entry_id": entry_id,
                    "account_id": line["account_id"],
                    "description": line["description"],
                    "debit": float(line["debit"]),
                    "credit": float(line["credit"]),
                }
            )

        return {
            "journal_entry_id": int(entry_id),
            "entry_number": entry_number,
            "debit": float(debit_total),
            "credit": float(credit_total),
        }
