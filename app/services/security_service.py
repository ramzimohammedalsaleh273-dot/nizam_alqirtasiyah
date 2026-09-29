
import sqlite3
import hashlib
from pathlib import Path

class SecurityService:
    def __init__(self, db_path=None):
        self.db=Path(db_path or Path(__file__).resolve().parents[2] / "database" / "nizam_alqirtasiyah.db")

    def _hash(self,password):
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def users(self):
        con=sqlite3.connect(self.db)
        con.row_factory=sqlite3.Row
        try:
            return [dict(x) for x in con.execute(
                "SELECT id,username FROM users ORDER BY id"
            ).fetchall()]
        finally:
            con.close()

    def authenticate(self,username,password):
        con=sqlite3.connect(self.db)
        con.row_factory=sqlite3.Row
        try:
            row=con.execute(
                "SELECT * FROM users WHERE username=? LIMIT 1",
                (username,)
            ).fetchone()

            if not row:
                return None

            data=dict(row)
            stored=data.get("password_hash") or data.get("password")
            if not stored:
                return None

            valid=stored == self._hash(password) or stored == password

            if not valid:
                return None

            con.execute("""
                INSERT INTO erp_login_sessions(user_id,status)
                VALUES (?,?)
            """,(data["id"],"ACTIVE"))
            con.commit()

            return data
        finally:
            con.close()

    def has_permission(self,user_id,permission_code):
        con=sqlite3.connect(self.db)
        try:
            row=con.execute("""
                SELECT 1
                FROM erp_user_roles ur
                JOIN erp_role_permissions rp ON rp.role_id=ur.role_id
                JOIN erp_permissions p ON p.id=rp.permission_id
                WHERE ur.user_id=? AND p.code=? AND p.is_active=1
                LIMIT 1
            """,(user_id,permission_code)).fetchone()
            return bool(row)
        finally:
            con.close()
