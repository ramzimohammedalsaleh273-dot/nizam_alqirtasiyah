from sqlalchemy import text
from app.database.connection import get_session


class PermissionService:
    """طبقة صلاحيات موحدة للعمليات الحساسة مع ترقية آمنة للمخطط القديم."""

    DEFAULTS = [
        ("sale.view", "عرض المبيعات"), ("sale.create", "إنشاء فاتورة بيع"),
        ("sale.edit", "تعديل فاتورة بيع"), ("sale.delete", "حذف/إلغاء فاتورة بيع"),
        ("sale.print", "طباعة فاتورة بيع"), ("sale.export", "تصدير المبيعات"),
        ("sale.approve", "اعتماد فاتورة بيع"), ("sale.price_edit", "تعديل سعر البيع"),
        ("sale.discount_edit", "تعديل الخصم"), ("sale.return.create", "مرتجع مبيعات"),
        ("purchase.view", "عرض المشتريات"), ("purchase.create", "إنشاء فاتورة شراء"),
        ("purchase.edit", "تعديل فاتورة شراء"), ("purchase.delete", "حذف/إلغاء فاتورة شراء"),
        ("purchase.print", "طباعة المشتريات"), ("purchase.export", "تصدير المشتريات"),
        ("purchase.request.create", "إنشاء طلب شراء"), ("purchase.request.approve", "اعتماد طلب شراء"),
        ("purchase.order.create", "إنشاء أمر شراء"), ("purchase.order.receive", "استلام أمر شراء"),
        ("purchase.return.create", "مرتجع مشتريات"),
        ("inventory.view", "عرض المخزون"), ("inventory.create", "إضافة صنف"),
        ("inventory.edit", "تعديل صنف"), ("inventory.delete", "حذف/تعطيل صنف"),
        ("inventory.adjust", "تعديل مخزون"), ("inventory.transfer", "تحويل مخزون"),
        ("inventory.stocktake", "الجرد"), ("inventory.negative_sale", "السماح بالبيع من المخزون السالب"),
        ("customer.view", "عرض العملاء"), ("customer.create", "إضافة عميل"),
        ("customer.edit", "تعديل عميل"), ("customer.delete", "حذف/تعطيل عميل"),
        ("customer.statement", "كشف حساب عميل"), ("customer.receipt", "سند قبض من عميل"),
        ("supplier.view", "عرض الموردين"), ("supplier.create", "إضافة مورد"),
        ("supplier.edit", "تعديل مورد"), ("supplier.delete", "حذف/تعطيل مورد"),
        ("supplier.statement", "كشف حساب مورد"), ("supplier.payment", "سند صرف لمورد"),
        ("treasury.view", "عرض الخزينة"), ("treasury.payment", "دفع خزينة"),
        ("treasury.receipt", "تحصيل خزينة"), ("treasury.transfer", "تحويل بين حسابات الخزينة"),
        ("treasury.cashier.open", "فتح جلسة كاشير"), ("treasury.cashier.close", "إغلاق جلسة كاشير"),
        ("accounting.view", "عرض المحاسبة"), ("accounting.edit", "تعديل قيد"),
        ("accounting.post", "ترحيل محاسبي"), ("accounting.period.close", "إغلاق الفترة المالية"),
        ("report.view", "عرض التقارير"), ("report.export", "تصدير التقارير"),
        ("report.print", "طباعة التقارير"), ("approval.view", "عرض الاعتمادات"),
        ("approval.approve", "اعتماد العمليات"), ("audit.view", "عرض سجل التدقيق"),
        ("document.view", "عرض المستندات"), ("document.create", "إضافة مستند"),
        ("document.delete", "حذف مستند"), ("user.view", "عرض المستخدمين"),
        ("user.create", "إضافة مستخدم"), ("user.edit", "تعديل مستخدم"),
        ("user.delete", "حذف مستخدم"), ("permission.manage", "إدارة الصلاحيات"),
        ("settings.view", "عرض الإعدادات"), ("settings.edit", "تعديل الإعدادات"),
        ("backup.create", "إنشاء نسخة احتياطية"), ("backup.restore", "استعادة نسخة احتياطية"),
        ("backup.verify", "فحص نسخة احتياطية"), ("sync.view", "عرض المزامنة"),
        ("sync.manage", "إدارة المزامنة"),
    ]

    @staticmethod
    def _columns(s, table):
        return {row[1] for row in s.execute(text(f"PRAGMA table_info({table})")).fetchall()}

    @classmethod
    def _upgrade_legacy_tables(cls, s):
        """توافق مع قواعد البيانات المنشأة قبل توحيد أسماء أعمدة الصلاحيات."""
        for table, column, ddl in (
            ("erp_permissions", "name_ar", "ALTER TABLE erp_permissions ADD COLUMN name_ar VARCHAR(200) DEFAULT ''"),
            ("erp_roles", "name_ar", "ALTER TABLE erp_roles ADD COLUMN name_ar VARCHAR(150) DEFAULT ''"),
        ):
            cols = cls._columns(s, table)
            if column not in cols:
                s.execute(text(ddl))

        cols = cls._columns(s, "erp_permissions")
        if "name" in cols:
            s.execute(text("UPDATE erp_permissions SET name_ar=COALESCE(NULLIF(name_ar,''),name)"))
        elif "description" in cols:
            s.execute(text("UPDATE erp_permissions SET name_ar=COALESCE(NULLIF(name_ar,''),description)"))

        cols = cls._columns(s, "erp_roles")
        if "name" in cols:
            s.execute(text("UPDATE erp_roles SET name_ar=COALESCE(NULLIF(name_ar,''),name)"))
        elif "description" in cols:
            s.execute(text("UPDATE erp_roles SET name_ar=COALESCE(NULLIF(name_ar,''),description)"))

    @classmethod
    def ensure_schema(cls, s):
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS erp_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code VARCHAR(120) NOT NULL UNIQUE,
                name_ar VARCHAR(200) NOT NULL DEFAULT '',
                is_active INTEGER NOT NULL DEFAULT 1
            )
        """))
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS erp_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code VARCHAR(80) NOT NULL UNIQUE,
                name_ar VARCHAR(150) NOT NULL DEFAULT '',
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
        cls._upgrade_legacy_tables(s)

        permission_cols = cls._columns(s, "erp_permissions")
        for code, name in cls.DEFAULTS:
            values = {"code": code, "name_ar": name, "name": name, "module": code.split(".", 1)[0]}
            fields = [k for k in ("code", "name", "name_ar", "module", "is_active") if k in permission_cols]
            params = {k: values[k] for k in fields if k != "is_active"}
            if "is_active" in fields:
                params["is_active"] = 1
            s.execute(
                text(f"INSERT OR IGNORE INTO erp_permissions({",".join(fields)}) VALUES({",".join(":"+k for k in fields)})"),
                params,
            )

        role_cols = cls._columns(s, "erp_roles")
        role_values = {"code": "admin", "name": "مدير النظام", "name_ar": "مدير النظام", "is_active": 1}
        role_fields = [k for k in ("code", "name", "name_ar", "is_active") if k in role_cols]
        role_params = {k: role_values[k] for k in role_fields}
        s.execute(
            text(f"INSERT OR IGNORE INTO erp_roles({",".join(role_fields)}) VALUES({",".join(":"+k for k in role_fields)})"),
            role_params,
        )
        admin_role = s.execute(text("SELECT id FROM erp_roles WHERE code='admin' AND COALESCE(is_active,1)=1")).scalar()
        if admin_role is None:
            raise RuntimeError("تعذر إنشاء دور مدير النظام")
        s.execute(text("""
            INSERT OR IGNORE INTO erp_role_permissions(role_id,permission_id)
            SELECT :role,id FROM erp_permissions WHERE is_active=1
        """), {"role": admin_role})

        count = int(s.execute(text("SELECT COUNT(*) FROM erp_user_roles")).scalar() or 0)
        if count == 0:
            tables = {r[0] for r in s.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()}
            if "users" in tables:
                cols = cls._columns(s, "users")
                active = "is_active" if "is_active" in cols else ("active" if "active" in cols else None)
                sql = "SELECT id FROM users"
                if active:
                    sql += f" WHERE COALESCE({active},1)=1"
                sql += " ORDER BY id LIMIT 1"
                user_id = s.execute(text(sql)).scalar()
                if user_id is not None:
                    s.execute(text("INSERT OR IGNORE INTO erp_user_roles(user_id,role_id) VALUES(:user,:role)"),
                              {"user": int(user_id), "role": int(admin_role)})

    @classmethod
    def default_user_id(cls):
        with get_session() as s:
            cls.ensure_schema(s)
            row = s.execute(text("""
                SELECT u.id FROM users u
                JOIN erp_user_roles ur ON ur.user_id=u.id
                JOIN erp_roles r ON r.id=ur.role_id
                WHERE COALESCE(r.is_active,1)=1 ORDER BY u.id LIMIT 1
            """)).fetchone()
            s.commit()
            return int(row[0]) if row else None

    @classmethod
    def has_in_session(cls, s, user_id, permission_code):
        if user_id is None:
            return False
        cls.ensure_schema(s)
        row = s.execute(text("""
            SELECT 1 FROM erp_user_roles ur
            JOIN erp_role_permissions rp ON rp.role_id=ur.role_id
            JOIN erp_permissions p ON p.id=rp.permission_id
            JOIN erp_roles r ON r.id=ur.role_id
            WHERE ur.user_id=:user AND p.code=:code
              AND COALESCE(p.is_active,1)=1 AND COALESCE(r.is_active,1)=1 LIMIT 1
        """), {"user": int(user_id), "code": permission_code}).fetchone()
        return bool(row)

    @classmethod
    def has(cls, user_id, permission_code):
        if user_id is None:
            return False
        with get_session() as s:
            return cls.has_in_session(s, user_id, permission_code)

    @classmethod
    def require(cls, user_id, permission_code):
        if not cls.has(user_id, permission_code):
            raise PermissionError(f"المستخدم {user_id} لا يملك الصلاحية: {permission_code}")
        return True
