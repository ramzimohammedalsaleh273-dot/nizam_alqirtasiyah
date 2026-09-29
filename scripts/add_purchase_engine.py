from pathlib import Path

p=Path("app/services/erp_engine.py")
s=p.read_text(encoding="utf-8")

marker="    def receive_purchase("
if "def create_purchase(" not in s:
    method='''    def create_purchase(self, supplier_id, items):
        if not items:
            raise ERPError("لا توجد أصناف في أمر الشراء")
        with self.connect() as con:
            total=0
            rows=[]
            for item in items:
                product=self._product(con,item["product_id"])
                qty=float(item["quantity"])
                cost=float(item["unit_cost"])
                if qty<=0 or cost<0:
                    raise ERPError("كمية أو تكلفة غير صحيحة")
                line=qty*cost
                total+=line
                rows.append((product,qty,cost,line))
            number=self._next_number(con,"PO","purchase_orders","order_number")
            data={
                "order_number":number,
                "supplier_id":supplier_id,
                "status":"DRAFT",
                "total_amount":total,
            }
            oid=self._insert_dynamic(con,"purchase_orders",data)
            for product,qty,cost,line in rows:
                self._insert_dynamic(con,"purchase_order_items",{
                    "purchase_order_id":oid,
                    "product_id":product["id"],
                    "quantity":qty,
                    "unit_cost":cost,
                    "total":line,
                })
            return {"purchase_id":oid,"total":total,"status":"CREATED"}

'''
    s=s.replace(marker,method+marker)

p.write_text(s,encoding="utf-8")
print("CREATE_PURCHASE: ADDED")
