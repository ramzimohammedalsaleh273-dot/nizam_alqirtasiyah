from datetime import datetime
from sqlalchemy import text
from app.database.connection import get_session


class PartyMasterService:
    @staticmethod
    def _create(table, code_field, code, name, phone=None, credit_limit=0):
        if table not in ("customers", "suppliers"):
            raise ValueError("نوع الطرف غير مسموح")
        with get_session() as s:
            cols={r[1] for r in s.execute(text(f'PRAGMA table_info({table})')).fetchall()}
            if not cols: raise ValueError(f"الجدول غير موجود: {table}")
            code=str(code or '').strip(); name=str(name or '').strip()
            if not code or not name: raise ValueError("الكود والاسم مطلوبان")
            exists=s.execute(text(f'SELECT id FROM {table} WHERE {code_field}=:code LIMIT 1'),{"code":code}).fetchone()
            if exists: raise ValueError("الكود مستخدم مسبقًا")
            data={code_field:code,"name":name,"phone":phone,"credit_limit":float(credit_limit or 0),"current_balance":0,"is_active":1,"created_at":datetime.now().isoformat(),"updated_at":datetime.now().isoformat()}
            data={k:v for k,v in data.items() if k in cols}
            keys=", ".join(data); binds=", ".join(':'+k for k in data)
            s.execute(text(f'INSERT INTO {table} ({keys}) VALUES ({binds})'),data)
            entity_id=int(s.execute(text('SELECT last_insert_rowid()')).scalar())
            s.commit()
            return entity_id

    @classmethod
    def create_customer(cls, code, name, phone=None, credit_limit=0):
        return cls._create("customers","customer_code",code,name,phone,credit_limit)

    @classmethod
    def create_supplier(cls, code, name, phone=None, credit_limit=0):
        return cls._create("suppliers","supplier_code",code,name,phone,credit_limit)
