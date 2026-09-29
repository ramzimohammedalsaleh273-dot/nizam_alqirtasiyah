import inspect
from app.services.erp_engine import ERP

print("="*78)
print("ERP ENGINE REAL SIGNATURES")
print("="*78)

for name in [
    "create_purchase",
    "receive_purchase",
    "create_sale",
    "dashboard",
    "health_check"
]:
    fn=getattr(ERP,name,None)
    print("\n"+name)
    print(inspect.signature(fn) if fn else "NOT FOUND")
    if fn:
        print(inspect.getdoc(fn) or "NO DOCSTRING")

print("\nSTATUS: SUCCESS")
print("="*78)
