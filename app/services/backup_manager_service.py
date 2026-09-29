from pathlib import Path
import sqlite3
from app.core.config import PROJECT_ROOT
from app.services.backup_service import BackupService


class BackupManagerService:
    @staticmethod
    def list_backups(directory=None):
        root = Path(directory or (PROJECT_ROOT / "backups"))
        if not root.exists():
            return []
        rows = []
        for path in sorted(root.glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                size = path.stat().st_size
                with sqlite3.connect(path) as con:
                    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
                rows.append({"path": path, "size": size, "integrity": integrity, "valid": integrity == "ok"})
            except Exception as exc:
                rows.append({"path": path, "size": 0, "integrity": str(exc), "valid": False})
        return rows

    @staticmethod
    def verify(path):
        return BackupService.verify_backup(path)

    @staticmethod
    def restore(path):
        return BackupService.restore_backup(path)
