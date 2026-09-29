from datetime import datetime
from pathlib import Path
import sqlite3

from app.core.config import DATABASE_PATH


class BackupService:
    """نسخ احتياطي آمن لقاعدة SQLite مع التحقق من سلامة النسخة."""

    @staticmethod
    def create_backup(destination_dir="backups"):
        source = Path(DATABASE_PATH)
        if not source.exists():
            raise FileNotFoundError(f"قاعدة البيانات غير موجودة: {source}")

        target_dir = Path(destination_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = target_dir / f"nizam_alqirtasiyah_{timestamp}.db"

        source_con = sqlite3.connect(source)
        target_con = sqlite3.connect(target)
        try:
            source_con.backup(target_con)
            target_con.commit()

            integrity = target_con.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]
            if integrity != "ok":
                raise RuntimeError(
                    f"فشل التحقق من النسخة الاحتياطية: {integrity}"
                )
        finally:
            target_con.close()
            source_con.close()

        return target
