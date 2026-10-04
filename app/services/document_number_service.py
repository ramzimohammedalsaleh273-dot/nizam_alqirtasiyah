from datetime import datetime
from sqlalchemy import text


class DocumentNumberService:
    """مولد أرقام مستندات آمن ومتزامن مع البيانات الموجودة."""

    TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS document_number_sequences (
        document_type VARCHAR(50) NOT NULL,
        sequence_year INTEGER NOT NULL,
        next_number INTEGER NOT NULL DEFAULT 1,
        prefix VARCHAR(50) NOT NULL,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (document_type, sequence_year)
    )
    """

    @classmethod
    def ensure_table(cls, session):
        session.execute(text(cls.TABLE_SQL))

    @classmethod
    def _max_existing_number(cls, session, document_type, prefix, year):
        """يقرأ أكبر رقم مستخدم فعليًا حتى لا يعيد المولد رقمًا موجودًا."""
        if document_type == "SALE" and prefix == "INV":
            row = session.execute(
                text("""
                    SELECT COALESCE(
                        MAX(CAST(substr(invoice_number, length(:prefix_year) + 1) AS INTEGER)),
                        0
                    )
                    FROM sales
                    WHERE invoice_number LIKE :pattern
                """),
                {
                    "prefix_year": f"{prefix}-{year}-",
                    "pattern": f"{prefix}-{year}-%",
                },
            ).scalar()
            return int(row or 0)
        return 0

    @classmethod
    def next_number(cls, session, document_type, prefix=None, year=None, width=6):
        document_type = str(document_type).strip().upper()
        if not document_type:
            raise ValueError("نوع المستند مطلوب")

        year = int(year or datetime.now().year)
        prefix = str(prefix or document_type).strip()
        if width < 1:
            raise ValueError("عرض رقم المستند غير صالح")

        cls.ensure_table(session)

        existing_max = cls._max_existing_number(session, document_type, prefix, year)
        row = session.execute(
            text("""
                SELECT next_number
                FROM document_number_sequences
                WHERE document_type=:type AND sequence_year=:year
            """),
            {"type": document_type, "year": year},
        ).scalar()

        next_number = int(row or 1)
        if existing_max + 1 > next_number:
            next_number = existing_max + 1

        session.execute(
            text("""
                INSERT INTO document_number_sequences
                (document_type, sequence_year, next_number, prefix, updated_at)
                VALUES (:type, :year, :next_number, :prefix, CURRENT_TIMESTAMP)
                ON CONFLICT(document_type, sequence_year) DO UPDATE SET
                    next_number=excluded.next_number,
                    prefix=excluded.prefix,
                    updated_at=CURRENT_TIMESTAMP
            """),
            {
                "type": document_type,
                "year": year,
                "next_number": next_number + 1,
                "prefix": prefix,
            },
        )

        return f"{prefix}-{year}-{next_number:0{width}d}"
