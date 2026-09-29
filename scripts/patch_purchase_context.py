from pathlib import Path

p=Path("app/services/erp_engine.py")
s=p.read_text(encoding="utf-8")

old='''            data={
                "order_number":number,
                "supplier_id":supplier_id,
                "status":"DRAFT",
                "total_amount":total,
            }'''

new='''            branch = con.execute("SELECT id FROM branches ORDER BY id LIMIT 1").fetchone()
            warehouse = con.execute("SELECT id FROM warehouses ORDER BY id LIMIT 1").fetchone()

            data={
                "order_number":number,
                "supplier_id":supplier_id,
                "status":"DRAFT",
                "total_amount":total,
            }

            if branch and "branch_id" in self._columns(con, "purchase_orders"):
                data["branch_id"] = branch[0]

            if warehouse and "warehouse_id" in self._columns(con, "purchase_orders"):
                data["warehouse_id"] = warehouse[0]'''

if old not in s:
    print("TARGET BLOCK NOT FOUND")
else:
    p.write_text(s.replace(old,new),encoding="utf-8")
    print("PURCHASE BRANCH/WAREHOUSE LINK: ADDED")
