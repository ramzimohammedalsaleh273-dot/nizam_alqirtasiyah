import sqlite3
import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "database" / "nizam_alqirtasiyah.db"
OUT_PATH = BASE_DIR / "database" / "metadata" / "database_schema.json"

connection = sqlite3.connect(DB_PATH)
connection.execute("PRAGMA foreign_keys = ON")

tables = connection.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
      AND name NOT LIKE 'sqlite_%'
    ORDER BY name
""").fetchall()

result = {
    "generated_at": datetime.now().isoformat(),
    "database": str(DB_PATH),
    "table_count": len(tables),
    "tables": {}
}

for (table_name,) in tables:
    columns = connection.execute(
        f'PRAGMA table_info("{table_name}")'
    ).fetchall()

    foreign_keys = connection.execute(
        f'PRAGMA foreign_key_list("{table_name}")'
    ).fetchall()

    result["tables"][table_name] = {
        "columns": [
            {
                "cid": row[0],
                "name": row[1],
                "type": row[2],
                "not_null": bool(row[3]),
                "default": row[4],
                "primary_key": bool(row[5])
            }
            for row in columns
        ],
        "foreign_keys": [
            {
                "table": row[2],
                "column": row[3],
                "references": row[4]
            }
            for row in foreign_keys
        ]
    }

connection.close()

OUT_PATH.write_text(
    json.dumps(result, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print("=" * 70)
print("فحص قاعدة البيانات مكتمل")
print("=" * 70)
print(f"عدد الجداول: {len(tables)}")
print(f"ملف البنية: {OUT_PATH}")
print("=" * 70)
