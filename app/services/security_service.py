import hashlib
import sqlite3
import uuid
from pathlib import Path

import bcrypt


class SecurityService:
    """مصادقة وصلاحيات متوافقة مع مخطط قاعدة البيانات الحالي والقديم."""

    BCRYPT_PREFIXES = ("$2a$", "$2b$", "$2y$")

    def __init__(self, db_path=None):
        self.db = Path(
            db_path
            or Path(__file__).resolve().parents[2]
            / "database"
            / "nizam_alqirtasiyah.db"
        )

    @staticmethod
    def _legacy_hash(password):
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    @staticmethod
    def _hash(password):
        return bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

    @staticmethod
    def _verify_bcrypt(password, stored):
        try:
            return bcrypt.checkpw(
                password.encode("utf-8"),
                stored.encode("utf-8"),
            )
        except (ValueError, TypeError):
            return False

    @staticmethod
    def _columns(con, table):
        return {
            row[1]
            for row in con.execute(
                f'PRAGMA table_info("{table}")'
            ).fetchall()
        }

    @staticmethod
    def _table_exists(con, table):
        return bool(con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone())

    def users(self):
        con = sqlite3.connect(self.db)
        con.row_factory = sqlite3.Row
        try:
            cols = self._columns(con, "users")
            active_col = "is_active" if "is_active" in cols else "active"
            return [
                dict(x)
                for x in con.execute(
                    f"SELECT id, username, {active_col} AS active FROM users ORDER BY id"
                ).fetchall()
            ]
        finally:
            con.close()

    def authenticate(self, username, password):
        if not username or not password:
            return None

        con = sqlite3.connect(self.db)
        con.row_factory = sqlite3.Row
        try:
            row = con.execute(
                "SELECT * FROM users WHERE username=? LIMIT 1",
                (username,),
            ).fetchone()
            if not row:
                return None

            data = dict(row)
            active = data.get("is_active", data.get("active", 1))
            if not active or data.get("is_locked", 0):
                return None

            stored = str(data.get("password_hash") or "").strip()
            if not stored:
                return None

            valid = (
                stored.startswith(self.BCRYPT_PREFIXES)
                and self._verify_bcrypt(password, stored)
            )

            legacy_valid = (
                not valid
                and (
                    stored == self._legacy_hash(password)
                    or stored == password
                )
            )

            if not valid and not legacy_valid:
                if "failed_login_attempts" in data:
                    con.execute(
                        "UPDATE users SET failed_login_attempts=COALESCE(failed_login_attempts,0)+1 WHERE id=?",
                        (data["id"],),
                    )
                    con.commit()
                return None

            if legacy_valid:
                new_hash = self._hash(password)
                updates = ["password_hash=?"]
                params = [new_hash]
                if "password_changed_at" in data:
                    updates.append("password_changed_at=CURRENT_TIMESTAMP")
                if "failed_login_attempts" in data:
                    updates.append("failed_login_attempts=0")
                params.append(data["id"])
                con.execute(
                    f"UPDATE users SET {', '.join(updates)} WHERE id=?",
                    params,
                )
                con.commit()
                data["password_hash"] = new_hash

            if "last_login_at" in data:
                con.execute(
                    "UPDATE users SET last_login_at=CURRENT_TIMESTAMP, failed_login_attempts=0 WHERE id=?",
                    (data["id"],),
                )

            # يدعم نظام الجلسات الحديث، أو جدول الجلسات القديم إن كان هو الموجود.
            session_table = None
            if self._table_exists(con, "erp_login_sessions"):
                session_table = "erp_login_sessions"
            elif self._table_exists(con, "user_sessions"):
                session_table = "user_sessions"

            if session_table:
                cols = self._columns(con, session_table)
                values = {"user_id": data["id"]}
                if "status" in cols:
                    values["status"] = "ACTIVE"
                if "is_active" in cols:
                    values["is_active"] = 1
                if "session_token" in cols:
                    values["session_token"] = uuid.uuid4().hex
                if "login_at" in cols:
                    values["login_at"] = None
                if "last_activity_at" in cols:
                    values["last_activity_at"] = None

                values = {k: v for k, v in values.items() if k in cols}
                keys = list(values)
                placeholders = []
                params = {}
                for key in keys:
                    if values[key] is None and key in ("login_at", "last_activity_at"):
                        placeholders.append("CURRENT_TIMESTAMP")
                    else:
                        placeholders.append(f":{key}")
                        params[key] = values[key]

                con.execute(
                    f'INSERT INTO "{session_table}" ({", ".join(keys)}) VALUES ({", ".join(placeholders)})',
                    params,
                )

            con.commit()
            return data
        finally:
            con.close()

    def has_permission(self, user_id, permission_code):
        con = sqlite3.connect(self.db)
        try:
            # النظام الجديد إن كان موجودًا.
            if all(
                self._table_exists(con, table)
                for table in (
                    "erp_user_roles",
                    "erp_role_permissions",
                    "erp_permissions",
                )
            ):
                row = con.execute(
                    """
                    SELECT 1
                    FROM erp_user_roles ur
                    JOIN erp_role_permissions rp ON rp.role_id=ur.role_id
                    JOIN erp_permissions p ON p.id=rp.permission_id
                    WHERE ur.user_id=? AND p.code=? AND COALESCE(p.is_active,1)=1
                    LIMIT 1
                    """,
                    (user_id, permission_code),
                ).fetchone()
                if row:
                    return True

            # التوافق مع الجداول المنشأة في المراحل الأولى.
            if all(
                self._table_exists(con, table)
                for table in ("user_roles", "role_permissions", "permissions")
            ):
                row = con.execute(
                    """
                    SELECT 1
                    FROM user_roles ur
                    JOIN role_permissions rp ON rp.role_id=ur.role_id
                    JOIN permissions p ON p.id=rp.permission_id
                    WHERE ur.user_id=? AND p.code=?
                    LIMIT 1
                    """,
                    (user_id, permission_code),
                ).fetchone()
                return bool(row)

            return False
        finally:
            con.close()
