from pathlib import Path
p=Path("app/services/erp_engine.py")
s=p.read_text(encoding="utf-8")
old='''                self._insert_dynamic(con,"purchase_order_items",{
                    "purchase_order_id":oid,
                    "product_id":product["id"],
                    "quantity":qty,
                    "unit_cost":cost,
                    "total":line,
                })'''
new='''                item_data={
                    "purchase_order_id":oid,
                    "order_id":oid,
                    "product_id":product["id"],
                    "quantity":qty,
                    "unit_cost":cost,
                    "total":line,
                }
                self._insert_dynamic(con,"purchase_order_items",item_data)'''
if old in s:
    p.write_text(s.replace(old,new),encoding="utf-8")
    print("PURCHASE ITEM LINK: FIXED")
else:
    print("TARGET BLOCK NOT FOUND")
