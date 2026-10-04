from sqlalchemy import text
from app.database.connection import get_session

class PermissionService:
    ENFORCE_PERMISSIONS = False
    DEFAULTS=[('sale.view','عرض المبيعات'),('sale.create','إنشاء فاتورة بيع'),('sale.edit','تعديل فاتورة بيع'),('sale.delete','حذف فاتورة بيع'),('sale.discount_edit','تعديل الخصم'),('sale.return.create','مرتجع مبيعات'),('purchase.view','عرض المشتريات'),('purchase.create','إنشاء فاتورة شراء'),('purchase.edit','تعديل فاتورة شراء'),('purchase.delete','حذف فاتورة شراء'),('purchase.return.create','مرتجع مشتريات'),('inventory.view','عرض المخزون'),('inventory.create','إضافة صنف'),('inventory.edit','تعديل صنف'),('inventory.delete','حذف صنف'),('inventory.adjust','تعديل المخزون'),('inventory.stocktake','الجرد'),('customer.view','عرض العملاء'),('customer.create','إضافة عميل'),('customer.edit','تعديل عميل'),('customer.delete','حذف عميل'),('customer.receipt','قبض من عميل'),('supplier.view','عرض الموردين'),('supplier.create','إضافة مورد'),('supplier.edit','تعديل مورد'),('supplier.delete','حذف مورد'),('supplier.payment','دفع لمورد'),('treasury.view','عرض الخزينة'),('treasury.receipt','سند قبض'),('treasury.payment','سند صرف'),('treasury.transfer','تحويل خزينة'),('treasury.cashier.open','فتح وردية'),('treasury.cashier.close','إغلاق وردية'),('accounting.view','عرض المحاسبة'),('accounting.edit','تعديل المحاسبة'),('accounting.post','ترحيل محاسبي'),('report.view','عرض التقارير'),('report.export','تصدير التقارير'),('approval.view','عرض الاعتمادات'),('approval.approve','اعتماد العمليات'),('audit.view','عرض التدقيق'),('document.view','عرض المستندات'),('document.create','إضافة مستند'),('document.delete','حذف مستند'),('user.view','عرض المستخدمين'),('user.create','إضافة مستخدم'),('user.edit','تعديل مستخدم'),('user.delete','حذف مستخدم'),('permission.manage','إدارة الصلاحيات'),('settings.view','عرض الإعدادات'),('settings.edit','تعديل الإعدادات'),('backup.create','نسخة احتياطية'),('backup.restore','استعادة نسخة'),('sync.view','عرض المزامنة'),('sync.manage','إدارة المزامنة')]
    @staticmethod
    def _columns(s,table):
        try:return {r[1] for r in s.connection().exec_driver_sql(f'PRAGMA table_info({table})').fetchall()}
        except:return set()
    @classmethod
    def _compat(cls,s):
        for table,column,ddl in [('erp_permissions','name_ar','ALTER TABLE erp_permissions ADD COLUMN name_ar VARCHAR(200) DEFAULT \"\"'),('erp_roles','name_ar','ALTER TABLE erp_roles ADD COLUMN name_ar VARCHAR(150) DEFAULT \"\"')]:
            if column not in cls._columns(s,table):
                try:s.execute(text(ddl))
                except Exception:pass
        pc=cls._columns(s,'erp_permissions');rc=cls._columns(s,'erp_roles')
        if 'name' in pc and 'name_ar' in pc:s.execute(text("UPDATE erp_permissions SET name_ar=COALESCE(NULLIF(name_ar,''),name)"))
        if 'description' in pc and 'name_ar' in pc:s.execute(text("UPDATE erp_permissions SET name_ar=COALESCE(NULLIF(name_ar,''),description)"))
        if 'name' in rc and 'name_ar' in rc:s.execute(text("UPDATE erp_roles SET name_ar=COALESCE(NULLIF(name_ar,''),name)"))
        if 'description' in rc and 'name_ar' in rc:s.execute(text("UPDATE erp_roles SET name_ar=COALESCE(NULLIF(name_ar,''),description)"))
    @classmethod
    def ensure_schema(cls,s):
        s.execute(text("CREATE TABLE IF NOT EXISTS erp_permissions(id INTEGER PRIMARY KEY AUTOINCREMENT,code VARCHAR(120) UNIQUE NOT NULL,name_ar VARCHAR(200) DEFAULT '',is_active INTEGER DEFAULT 1)"))
        s.execute(text("CREATE TABLE IF NOT EXISTS erp_roles(id INTEGER PRIMARY KEY AUTOINCREMENT,code VARCHAR(80) UNIQUE NOT NULL,name_ar VARCHAR(150) DEFAULT '',is_active INTEGER DEFAULT 1)"))
        s.execute(text("CREATE TABLE IF NOT EXISTS erp_role_permissions(role_id INTEGER NOT NULL,permission_id INTEGER NOT NULL,PRIMARY KEY(role_id,permission_id))"))
        s.execute(text("CREATE TABLE IF NOT EXISTS erp_user_roles(user_id INTEGER NOT NULL,role_id INTEGER NOT NULL,PRIMARY KEY(user_id,role_id))"))
        cls._compat(s)
        for code,name in cls.DEFAULTS:s.execute(text("INSERT OR IGNORE INTO erp_permissions(code,name_ar,is_active) VALUES(:c,:n,1)"),{'c':code,'n':name})
        for code,name in [('admin','مدير النظام'),('cashier','كاشير'),('sales','مبيعات'),('inventory','مخزون'),('accountant','محاسب'),('purchasing','مشتريات'),('viewer','عرض')]:s.execute(text("INSERT OR IGNORE INTO erp_roles(code,name_ar,is_active) VALUES(:c,:n,1)"),{'c':code,'n':name})
        s.execute(text("CREATE TABLE IF NOT EXISTS permission_seed_state(id INTEGER PRIMARY KEY CHECK(id=1),manual_assignment_mode INTEGER NOT NULL DEFAULT 1)"));s.execute(text("INSERT OR IGNORE INTO permission_seed_state(id,manual_assignment_mode) VALUES(1,1)"))
    @classmethod
    def default_user_id(cls):
        with get_session() as s:cls.ensure_schema(s);row=s.execute(text("SELECT id FROM users ORDER BY id LIMIT 1")).first();s.commit();return int(row[0]) if row else None
    @classmethod
    def has_in_session(cls,s,user_id,permission_code):
        if not cls.ENFORCE_PERMISSIONS:return True
        if user_id is None:return False
        cls.ensure_schema(s);return bool(s.execute(text("SELECT 1 FROM erp_user_roles ur JOIN erp_role_permissions rp ON rp.role_id=ur.role_id JOIN erp_permissions p ON p.id=rp.permission_id WHERE ur.user_id=:u AND p.code=:c AND COALESCE(p.is_active,1)=1 LIMIT 1"),{'u':int(user_id),'c':permission_code}).first())
    @classmethod
    def has(cls,user_id,permission_code):
        if not cls.ENFORCE_PERMISSIONS:return True
        if user_id is None:return False
        with get_session() as s:return cls.has_in_session(s,user_id,permission_code)
    @classmethod
    def require(cls,user_id,permission_code):
        if not cls.has(user_id,permission_code):raise PermissionError(f'المستخدم {user_id} لا يملك الصلاحية: {permission_code}')
        return True
