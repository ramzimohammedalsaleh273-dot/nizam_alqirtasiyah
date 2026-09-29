import sys

packages = [
    ("sqlalchemy", "SQLAlchemy"),
    ("alembic", "Alembic"),
    ("pydantic", "Pydantic")
]

failed = []

for module_name, display_name in packages:
    try:
        module = __import__(module_name)
        version = getattr(module, "__version__", "installed")
        print(display_name + ": OK - " + str(version))
    except Exception as exc:
        print(display_name + ": FAILED - " + str(exc))
        failed.append(module_name)

if failed:
    print("MISSING_PACKAGES=" + ",".join(failed))
    sys.exit(1)

print("DEPENDENCIES: OK")
