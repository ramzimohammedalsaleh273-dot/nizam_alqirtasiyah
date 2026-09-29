from datetime import datetime
from pathlib import Path
import sqlite3

from app.core.config import DATABASE_PATH, PROJECT_ROOT


class BackupService:
    """نسخ احتياطي آمن لقاعدة SQLite مع التحقق من سلامة النسخة."""

    @staticmethod
    def create_backup(destination_dir=None):
        source = Path(DATABASE_PATH)
        if not source.exists():
            raise FileNotFoundError(f"قاعدة البيانات غير موجودة: {source}")

        target_dir = Path(destination_dir) if destination_dir else PROJECT_ROOT / "backups"
        target_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
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

    @staticmethod
    def verify_backup(backup_path):
        path = Path(backup_path)
        if not path.exists():
            raise FileNotFoundError(f"النسخة الاحتياطية غير موجودة: {path}")
        with sqlite3.connect(path) as con:
            integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                raise RuntimeError(f"فشل فحص سلامة النسخة: {integrity}")
            foreign_keys = con.execute("PRAGMA foreign_key_check").fetchall()
            if foreign_keys:
                raise RuntimeError(f"توجد مخالفات مفاتيح أجنبية: {len(foreign_keys)}")
        return True

    @staticmethod
    def restore_backup(backup_path):
        source = Path(backup_path)
        target = Path(DATABASE_PATH)
        if source.resolve() == target.resolve():
            raise ValueError("لا يمكن استعادة قاعدة البيانات من نفس الملف الحالي")

        BackupService.verify_backup(source)
        safety_backup = BackupService.create_backup(PROJECT_ROOT / "backups")
        temp = target.with_suffix(target.suffix + ".restore.tmp")

        if temp.exists():
            temp.unlink()

        source_con = sqlite3.connect(source)
        target_con = sqlite3.connect(temp)
        try:
            source_con.backup(target_con)
            target_con.commit()
            integrity = target_con.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                raise RuntimeError(f"فشل التحقق من قاعدة الاستعادة: {integrity}")
        finally:
            target_con.close()
            source_con.close()

        temp.replace(target)
        return target, safety_backup
