from datetime import datetime
from sqlalchemy import text
from app.database.connection import get_session


class ProductService:
    @staticmethod
    def create_product(sku,name_ar,cost_price,sale_price,barcode=None):
        sku=str(sku).strip(); name_ar=str(name_ar).strip()
        if not sku or not name_ar: raise ValueError("رمز الصنف واسم المنتج مطلوبان")
        if float(cost_price)<0 or float(sale_price)<0: raise ValueError("الأسعار لا يمكن أن تكون سالبة")
        with get_session() as s:
            if s.execute(text("SELECT 1 FROM products WHERE sku=:sku LIMIT 1"),{"sku":sku}).scalar():
                raise ValueError("رمز الصنف موجود مسبقاً")
            table_info=s.execute(text("PRAGMA table_info(products)")).fetchall()
            cols={r[1] for r in table_info}
            data={"sku":sku,"name_ar":name_ar,"name_en":name_ar,"cost_price":float(cost_price),"sale_price":float(sale_price),
                  "wholesale_price":float(sale_price),"school_price":float(sale_price),"corporate_price":float(sale_price),
                  "min_price":float(cost_price),"reorder_point":5,"min_stock":3,"max_stock":100,
                  "is_active":1,"created_at":datetime.now().isoformat(),"updated_at":datetime.now().isoformat()}

            # لا نفترض أن المعرف 1 موجود؛ نحل مرجع المفتاح الأجنبي من مخطط القاعدة.
            foreign_keys=s.execute(text("PRAGMA foreign_key_list(products)")).fetchall()
            fk_targets={row[3]: row[2] for row in foreign_keys}
            for field in ("category_id","unit_id"):
                if field not in cols:
                    continue
                target=fk_targets.get(field)
                if not target:
                    continue
                target_id=s.execute(
                    text(f"SELECT id FROM \"{target}\" ORDER BY id LIMIT 1")
                ).scalar()
                if target_id is not None:
                    data[field]=int(target_id)
                else:
                    notnull=next((bool(row[3]) for row in table_info if row[1]==field), False)
                    if notnull:
                        raise ValueError(f"لا يمكن إنشاء الصنف: لا توجد بيانات مرجعية للحقل {field}")
            data={k:v for k,v in data.items() if k in cols}
            names=list(data); marks=",".join(":"+k for k in names)
            s.execute(text('INSERT INTO products ('+','.join('"'+k+'"' for k in names)+') VALUES ('+marks+')'),data)
            product_id=s.execute(text("SELECT last_insert_rowid()")).scalar()
            if barcode and "product_barcodes" in [r[0] for r in s.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()]:
                s.execute(text("INSERT INTO product_barcodes(product_id,barcode,is_primary) VALUES(:id,:barcode,1)"),{"id":product_id,"barcode":str(barcode).strip()})
            s.commit()
            return int(product_id)
