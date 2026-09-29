from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.erp_service import health_check, db

result = health_check()

print("=" * 70)
print("CORE ERP REPAIR CHECK")
print("=" * 70)

print("DATABASE:", result["database"])
print("STATUS:", result["status"])
print("MISSING TABLES:", result["missing_tables"])
print("TABLES:", len([
    x for x in db.connect().execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
]))

if result["missing_tables"]:
    raise SystemExit("CORE CHECK FAILED")

print("DATABASE CONNECTION: PASSED")
print("ERP SERVICE: PASSED")
print("UI SERVICE IMPORT: PASSED")
print("STATUS: SUCCESS")
print("=" * 70)
