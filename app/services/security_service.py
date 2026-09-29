import hashlib
import sqlite3
from pathlib import Path

import bcrypt


class SecurityService:
    """
    طبقة المصادقة والصلاحيات.
    كلمات المرور الجديدة تُحفظ باستخدام bcrypt.
    الحسابات القديمة (SHA-256 أو النص الصريح) تُرقّى تلقائيًا بعد نجاح الدخول.
    """

    BCRYPT_PREFIXES = (b"$2a$", b"$2b$", b"$2y$")

    def __init__(self, db_path=None):
        self.db = Path(
            db_path
            or Path(__file__).resolve().parents[2]
            / "database"
            / "nizam_alqirtasiyah.db"
        )

    @staticmethod
    def _legacy_hash(password):
        return hashlib.sha256(
            password.encode("utf-8")
        ).hexdigest()

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

    def users(self):
        con = sqlite3.connect(self.db)
        con.row_factory = sqlite3.Row
        try:
            return [
                dict(x)
                for x in con.execute(
                    "SELECT id,username,active FROM users ORDER BY id"
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

            if "active" in data and not data["active"]:
                return None

            stored = str(data.get("password_hash") or "").strip()
            if not stored:
                return None

            # المسار الحديث.
            valid = stored.startswith(
                tuple(prefix.decode("ascii") for prefix in self.BCRYPT_PREFIXES)
            ) and self._verify_bcrypt(password, stored)

            # ترقية الحسابات القديمة عند أول دخول ناجح.
            legacy_valid = False
            if not valid:
                legacy_valid = (
                    stored == self._legacy_hash(password)
                    or stored == password
                )

            if not valid and not legacy_valid:
                return None

            if legacy_valid:
                new_hash = self._hash(password)
                con.execute(
                    "UPDATE users SET password_hash=? WHERE id=?",
                    (new_hash, data["id"]),
                )
                con.commit()
                data["password_hash"] = new_hash

            con.execute(
                """
                INSERT INTO erp_login_sessions(user_id,status)
                VALUES (?,?)
                """,
                (data["id"], "ACTIVE"),
            )
            con.commit()

            return data
        finally:
            con.close()

    def has_permission(self, user_id, permission_code):
        con = sqlite3.connect(self.db)
        try:
            row = con.execute(
                """
                SELECT 1
                FROM erp_user_roles ur
                JOIN erp_role_permissions rp
                    ON rp.role_id=ur.role_id
                JOIN erp_permissions p
                    ON p.id=rp.permission_id
                WHERE ur.user_id=?
                  AND p.code=?
                  AND p.is_active=1
                LIMIT 1
                """,
                (user_id, permission_code),
            ).fetchone()
            return bool(row)
        finally:
            con.close()
