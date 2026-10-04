from pathlib import Path
from sqlalchemy import inspect
from app.database.connection import engine
from app.models.core import Base

db = Path("database/nizam_alqirtasiyah.db")

if not db.exists():
    raise SystemExit("DATABASE_MISSING")

Base.metadata.create_all(bind=engine)

tables = inspect(engine).get_table_names()

required = [
    "companies",
    "branches",
    "products",
    "customers",
    "suppliers",
    "users",
    "audit_logs"
]

missing = [x for x in required if x not in tables]

if missing:
    print("MISSING_TABLES")
    for x in missing:
        print(x)
    raise SystemExit(1)

print("DATABASE_TEST_OK")
print("TABLE_COUNT:", len(tables))
for table in tables:
    print("-", table)
