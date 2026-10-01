from datetime import datetime
from sqlalchemy import text
from app.database.connection import get_session
from app.services.permission_service import PermissionService
from app.services.audit_service import AuditService


class ProductService:
    @staticmethod
    def create_product(sku,name_ar,cost_price,sale_price,barcode=None,opening_quantity=0,warehouse_id=1,user_id=None):
        sku=str(sku).strip(); name_ar=str(name_ar).strip()
        if not sku or not name_ar: raise ValueError("رمز الصنف واسم المنتج مطلوبان")
        if float(cost_price)<0 or float(sale_price)<0: raise ValueError("الأسعار لا يمكن أن تكون سالبة")
        with get_session() as s:
            PermissionService.ensure_schema(s)
            if user_id is None or not PermissionService.has_in_session(s, user_id, "inventory.create"):
                raise PermissionError("لا توجد صلاحية لإضافة صنف")
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
            opening = float(opening_quantity or 0)
            if opening < 0:
                raise ValueError("الكمية الافتتاحية لا يمكن أن تكون سالبة")
            if opening:
                wh = s.execute(text("SELECT id FROM warehouses WHERE id=:id"), {"id": int(warehouse_id)}).scalar()
                if wh is None:
                    raise ValueError("المستودع المحدد غير موجود")
                stock = s.execute(text("SELECT id FROM stock_balances WHERE product_id=:p AND warehouse_id=:w"),
                                  {"p": product_id, "w": int(warehouse_id)}).scalar()
                if stock:
                    s.execute(text("UPDATE stock_balances SET quantity=COALESCE(quantity,0)+:q, average_cost=:c, last_movement_at=CURRENT_TIMESTAMP WHERE id=:id"),
                              {"q": opening, "c": float(cost_price), "id": stock})
                else:
                    s.execute(text("INSERT INTO stock_balances(product_id,warehouse_id,quantity,reserved_quantity,average_cost,last_movement_at) VALUES(:p,:w,:q,0,:c,CURRENT_TIMESTAMP)"),
                              {"p": product_id, "w": int(warehouse_id), "q": opening, "c": float(cost_price)})
                if "stock_movements" in [r[0] for r in s.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()]:
                    cols={r[1] for r in s.execute(text("PRAGMA table_info(stock_movements)")).fetchall()}
                    fields=["product_id","warehouse_id","quantity"]; vals=[":p",":w",":q"]; params={"p":product_id,"w":int(warehouse_id),"q":opening}
                    if "movement_type" in cols: fields.append("movement_type"); vals.append("'OPENING'")
                    if "notes" in cols: fields.append("notes"); vals.append(":n"); params["n"]="رصيد افتتاحي عند إنشاء الصنف"
                    if "created_at" in cols: fields.append("created_at"); vals.append("CURRENT_TIMESTAMP")
                    s.execute(text(f"INSERT INTO stock_movements({','.join(fields)}) VALUES({','.join(vals)})"), params)
            AuditService.log(s,"PRODUCT_CREATED","product",product_id,username=str(user_id))
            s.commit()
            return int(product_id)

    @staticmethod
    def update_product(product_id, sku, name_ar, cost_price, sale_price, user_id=None):
        sku=str(sku).strip(); name_ar=str(name_ar).strip()
        if not sku or not name_ar: raise ValueError("رمز الصنف واسم المنتج مطلوبان")
        if float(cost_price)<0 or float(sale_price)<0: raise ValueError("الأسعار لا يمكن أن تكون سالبة")
        with get_session() as s:
            PermissionService.ensure_schema(s)
            if user_id is None or not PermissionService.has_in_session(s, user_id, "inventory.edit"):
                raise PermissionError("لا توجد صلاحية لتعديل الصنف")
            duplicate=s.execute(text("SELECT id FROM products WHERE sku=:sku AND id<>:id LIMIT 1"),{"sku":sku,"id":product_id}).scalar()
            if duplicate: raise ValueError("رمز الصنف مستخدم لصنف آخر")
            cols={r[1] for r in s.execute(text("PRAGMA table_info(products)")).fetchall()}
            data={"sku":sku,"name_ar":name_ar,"cost_price":float(cost_price),"sale_price":float(sale_price),"updated_at":datetime.now().isoformat()}
            data={k:v for k,v in data.items() if k in cols}
            if not data: raise ValueError("لا توجد حقول قابلة للتحديث")
            assignments=", ".join(f'"{k}"=:{k}' for k in data)
            data["id"]=int(product_id)
            result=s.execute(text(f"UPDATE products SET {assignments} WHERE id=:id AND is_active=1"),data)
            if result.rowcount != 1: raise ValueError("الصنف غير موجود أو غير نشط")
            AuditService.log(s,"PRODUCT_UPDATED","product",product_id,username=str(user_id))
            s.commit()


    @staticmethod
    def deactivate_product(product_id, user_id=None):
        with get_session() as s:
            PermissionService.ensure_schema(s)
            if user_id is None or not PermissionService.has_in_session(s, user_id, "inventory.delete"):
                raise PermissionError("لا توجد صلاحية لتعطيل الصنف")
            result=s.execute(text("UPDATE products SET is_active=0, updated_at=CURRENT_TIMESTAMP WHERE id=:id AND is_active=1"),{"id":int(product_id)})
            if result.rowcount != 1:
                raise ValueError("الصنف غير موجود أو محذوف مسبقًا")
            AuditService.log(s,"PRODUCT_DEACTIVATED","product",product_id,username=str(user_id))
            s.commit()

    @staticmethod
    def adjust_quantity(product_id, warehouse_id, quantity, reason="تعديل كمية من بطاقة الصنف", user_id=None):
        from app.services.inventory_operations_service import InventoryOperationsService
        InventoryOperationsService.adjust(int(product_id), int(warehouse_id), float(quantity), reason, user_id=user_id)
