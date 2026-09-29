import sqlite3

c=sqlite3.connect(r"database\nizam_alqirtasiyah.db")
x=c.cursor()

print("=== طبقات التكلفة ===")

layers=[]

for qty,cost in x.execute("""
SELECT quantity,unit_cost
FROM stock_movements
WHERE product_id=1 AND warehouse_id=1
ORDER BY id
"""):
    qty=float(qty)
    cost=float(cost)

    if qty>0:
        layers.append([qty,cost])
    else:
        remaining=-qty
        while remaining>0 and layers:
            take=min(remaining,layers[0][0])
            layers[0][0]-=take
            remaining-=take
            if layers[0][0]<=0:
                layers.pop(0)

print("الطبقات المتبقية:")
total_qty=0
total_value=0

for qty,cost in layers:
    value=qty*cost
    total_qty+=qty
    total_value+=value
    print("الكمية:",qty,"التكلفة:",cost,"القيمة:",value)

print("\nإجمالي الكمية:",total_qty)
print("إجمالي القيمة:",total_value)
print("متوسط التكلفة:",total_value/total_qty if total_qty else 0)

print("\n=== جدول stock ===")
print(x.execute("""
SELECT product_id,warehouse_id,quantity,average_cost,
       quantity*average_cost
FROM stock
WHERE product_id=1 AND warehouse_id=1
""").fetchone())

print("\n=== حركات المخزون ===")
for r in x.execute("""
SELECT id,movement_type,quantity,unit_cost,reference_type,reference_id
FROM stock_movements
WHERE product_id=1 AND warehouse_id=1
ORDER BY id
"""):
    print(r)

c.close()
