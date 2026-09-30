from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import text
from app.database.connection import get_session


class TaxService:
    """محرك ضريبة قابل للتهيئة من إعدادات النظام، مع تحقق صارم من القيم."""

    DEFAULT_RATE = Decimal("0.15")

    @staticmethod
    def money(value):
        return Decimal(str(value)).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

    @classmethod
    def rate(cls):
        with get_session() as s:
            try:
                row = s.execute(
                    text("""
                        SELECT setting_value
                        FROM system_settings
                        WHERE setting_key IN ('VAT_RATE','vat_rate','tax_rate')
                        ORDER BY CASE setting_key
                            WHEN 'VAT_RATE' THEN 0
                            WHEN 'vat_rate' THEN 1
                            ELSE 2
                        END
                        LIMIT 1
                    """)
                ).fetchone()
                if row and row[0] is not None:
                    value = Decimal(str(row[0]).strip())
                    if value > 1:
                        value = value / 100
                    if Decimal("0") <= value <= Decimal("1"):
                        return value
            except Exception:
                pass
        return cls.DEFAULT_RATE

    @classmethod
    def calculate(cls, taxable_amount, rate=None):
        base = cls.money(taxable_amount)
        if base < 0:
            raise ValueError("المبلغ الخاضع للضريبة لا يمكن أن يكون سالبًا")
        r = cls.rate() if rate is None else Decimal(str(rate))
        if r > 1:
            r = r / 100
        if r < 0 or r > 1:
            raise ValueError("نسبة الضريبة غير صحيحة")
        tax = cls.money(base * r)
        return {
            "base": float(base),
            "rate": float(r),
            "tax": float(tax),
            "total": float(cls.money(base + tax)),
        }
