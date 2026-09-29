from pathlib import Path
p=Path("scripts/real_erp_test.py")
s=p.read_text(encoding="utf-8")
old='''    print("[3] RECEIVE")
    received=erp.receive_purchase(purchase["purchase_id"])
    print(received)'''
new='''    print("[3] RECEIVE")
    warehouse_id=warehouse[0]
    received=erp.receive_purchase(
        purchase["purchase_id"],
        warehouse_id,
        [{"product_id":product[0],"quantity":5,"unit_cost":10}]
    )
    print(received)'''
if old in s:
    p.write_text(s.replace(old,new),encoding="utf-8")
    print("RECEIVE TEST: FIXED")
else:
    print("TARGET NOT FOUND")
