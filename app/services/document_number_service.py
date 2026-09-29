from datetime import datetime
from sqlalchemy import text


class DocumentNumberService:
    """مولد أرقام مستندات ذري وآمن للتزامن داخل SQLite."""

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
    def next_number(cls, session, document_type, prefix=None, year=None, width=6):
        document_type = str(document_type).strip().upper()
        if not document_type:
            raise ValueError("نوع المستند مطلوب")
        year = int(year or datetime.now().year)
        prefix = str(prefix or document_type).strip()
        if width < 1:
            raise ValueError("عرض رقم المستند غير صالح")

        cls.ensure_table(session)
        # القفل الذري يمنع حصول عمليتين على الرقم نفسه عند الترحيل المتزامن.
        session.execute(text("BEGIN IMMEDIATE"))
        row = session.execute(
            text("""
                SELECT next_number
                FROM document_number_sequences
                WHERE document_type=:type AND sequence_year=:year
            """),
            {"type": document_type, "year": year},
        ).fetchone()

        if row is None:
            number = 1
            session.execute(
                text("""
                    INSERT INTO document_number_sequences
                    (document_type, sequence_year, next_number, prefix, updated_at)
                    VALUES (:type, :year, :next_number, :prefix, CURRENT_TIMESTAMP)
                """),
                {"type": document_type, "year": year, "next_number": 2, "prefix": prefix},
            )
        else:
            number = int(row[0])
            session.execute(
                text("""
                    UPDATE document_number_sequences
                    SET next_number=:next_number, prefix=:prefix, updated_at=CURRENT_TIMESTAMP
                    WHERE document_type=:type AND sequence_year=:year
                """),
                {
                    "type": document_type,
                    "year": year,
                    "next_number": number + 1,
                    "prefix": prefix,
                },
            )

        return f"{prefix}-{year}-{number:0{width}d}"
