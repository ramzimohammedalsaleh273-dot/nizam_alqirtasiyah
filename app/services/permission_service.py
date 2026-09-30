from sqlalchemy import text
from app.database.connection import get_session


class PermissionService:
    """طبقة صلاحيات موحدة للعمليات الحساسة مع تهيئة آمنة أولية للنظام."""

    DEFAULTS = [
        ("purchase.request.create", "إنشاء طلب شراء"),
        ("purchase.request.approve", "اعتماد طلب شراء"),
        ("purchase.order.create", "إنشاء أمر شراء"),
        ("purchase.order.receive", "استلام أمر شراء"),
        ("purchase.return.create", "مرتجع مشتريات"),
        ("sale.return.create", "مرتجع مبيعات"),
        ("treasury.payment", "دفع خزينة"),
        ("treasury.receipt", "تحصيل خزينة"),
        ("treasury.transfer", "تحويل بين حسابات الخزينة"),
        ("treasury.cashier.open", "فتح جلسة كاشير"),
        ("treasury.cashier.close", "إغلاق جلسة كاشير"),
        ("inventory.adjust", "تعديل مخزون"),
        ("inventory.transfer", "تحويل مخزون"),
        ("accounting.post", "ترحيل محاسبي"),
        ("backup.create", "إنشاء نسخة احتياطية"),
    ]

    @staticmethod
    def ensure_schema(s):
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS erp_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code VARCHAR(120) NOT NULL UNIQUE,
                name_ar VARCHAR(200) NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
            )
        """))
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS erp_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code VARCHAR(80) NOT NULL UNIQUE,
                name_ar VARCHAR(150) NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
            )
        """))
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS erp_role_permissions (
                role_id INTEGER NOT NULL,
                permission_id INTEGER NOT NULL,
                PRIMARY KEY(role_id,permission_id)
            )
        """))
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS erp_user_roles (
                user_id INTEGER NOT NULL,
                role_id INTEGER NOT NULL,
                PRIMARY KEY(user_id,role_id)
            )
        """))
        for code, name in PermissionService.DEFAULTS:
            s.execute(text("""
                INSERT OR IGNORE INTO erp_permissions(code,name_ar,is_active)
                VALUES(:code,:name,1)
            """), {"code": code, "name": name})
        s.execute(text("""
            INSERT OR IGNORE INTO erp_roles(code,name_ar,is_active)
            VALUES('admin','مدير النظام',1)
        """))
        admin_role = s.execute(
            text("SELECT id FROM erp_roles WHERE code='admin'")
        ).scalar()
        s.execute(text("""
            INSERT OR IGNORE INTO erp_role_permissions(role_id,permission_id)
            SELECT :role,id FROM erp_permissions WHERE is_active=1
        """), {"role": admin_role})

        # تهيئة أول مستخدم فعّال بدور مدير النظام عند عدم وجود أي ربط صلاحيات.
        count = int(s.execute(text("SELECT COUNT(*) FROM erp_user_roles")).scalar() or 0)
        if count == 0:
            tables = {
                r[0] for r in s.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )).fetchall()
            }
            if "users" in tables:
                cols = {r[1] for r in s.execute(text("PRAGMA table_info(users)")).fetchall()}
                active = "is_active" if "is_active" in cols else ("active" if "active" in cols else None)
                sql = "SELECT id FROM users"
                if active:
                    sql += f" WHERE COALESCE({active},1)=1"
                sql += " ORDER BY id LIMIT 1"
                user_id = s.execute(text(sql)).scalar()
                if user_id is not None:
                    s.execute(text("""
                        INSERT OR IGNORE INTO erp_user_roles(user_id,role_id)
                        VALUES(:user,:role)
                    """), {"user": int(user_id), "role": int(admin_role)})

    @classmethod
    def default_user_id(cls):
        with get_session() as s:
            cls.ensure_schema(s)
            row = s.execute(text("""
                SELECT u.id
                FROM users u
                JOIN erp_user_roles ur ON ur.user_id=u.id
                JOIN erp_roles r ON r.id=ur.role_id
                WHERE COALESCE(r.is_active,1)=1
                ORDER BY u.id LIMIT 1
            """)).fetchone()
            s.commit()
            return int(row[0]) if row else None

    @staticmethod
    def has_in_session(s, user_id, permission_code):
        if user_id is None:
            return False
        PermissionService.ensure_schema(s)
        row = s.execute(text("""
            SELECT 1
            FROM erp_user_roles ur
            JOIN erp_role_permissions rp ON rp.role_id=ur.role_id
            JOIN erp_permissions p ON p.id=rp.permission_id
            JOIN erp_roles r ON r.id=ur.role_id
            WHERE ur.user_id=:user
              AND p.code=:code
              AND COALESCE(p.is_active,1)=1
              AND COALESCE(r.is_active,1)=1
            LIMIT 1
        """), {"user": int(user_id), "code": permission_code}).fetchone()
        return bool(row)

    @classmethod
    def has(cls, user_id, permission_code):
        if user_id is None:
            return False
        with get_session() as s:
            try:
                return cls.has_in_session(s, user_id, permission_code)
            except Exception:
                s.rollback()
                raise

    @classmethod
    def require(cls, user_id, permission_code):
        if not cls.has(user_id, permission_code):
            raise PermissionError(f"المستخدم {user_id} لا يملك الصلاحية: {permission_code}")
        return True
