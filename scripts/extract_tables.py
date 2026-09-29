import sqlite3
from pathlib import Path

DB = Path("database/nizam_alqirtasiyah.db")
OUT = Path("database/TABLE_CONTENTS_FOR_CHAT.txt")

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

tables = [
    row[0]
    for row in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
]

with OUT.open("w", encoding="utf-8-sig") as f:

    f.write("=" * 100 + "\n")
    f.write("نظام القرطاسية - محتويات قاعدة البيانات\n")
    f.write("=" * 100 + "\n")
    f.write(f"عدد الجداول: {len(tables)}\n\n")

    for number, table in enumerate(tables, 1):

        f.write("\n" + "#" * 100 + "\n")
        f.write(f"TABLE {number}: {table}\n")
        f.write("#" * 100 + "\n")

        columns = con.execute(
            f'PRAGMA table_info("{table}")'
        ).fetchall()

        f.write("\n[الأعمدة]\n")

        for c in columns:
            f.write(
                f"الاسم={c['name']} | "
                f"النوع={c['type']} | "
                f"NULL={c['notnull']} | "
                f"DEFAULT={c['dflt_value']} | "
                f"PK={c['pk']}\n"
            )

        fks = con.execute(
            f'PRAGMA foreign_key_list("{table}")'
        ).fetchall()

        f.write("\n[العلاقات]\n")

        if fks:
            for fk in fks:
                f.write(
                    f"{fk['from']} -> "
                    f"{fk['table']}.{fk['to']} | "
                    f"UPDATE={fk['on_update']} | "
                    f"DELETE={fk['on_delete']}\n"
                )
        else:
            f.write("لا توجد علاقات مباشرة\n")

        count = con.execute(
            f'SELECT COUNT(*) FROM "{table}"'
        ).fetchone()[0]

        f.write(f"\n[عدد السجلات] {count}\n")

        f.write("\n[المحتويات]\n")

        if count == 0:
            f.write("الجدول فارغ\n")
            continue

        names = [c["name"] for c in columns]

        f.write(" | ".join(names) + "\n")
        f.write("-" * 100 + "\n")

        rows = con.execute(
            f'SELECT * FROM "{table}"'
        ).fetchall()

        for row_number, row in enumerate(rows, 1):

            values = []

            for name in names:

                value = row[name]

                if value is None:
                    value = "NULL"
                elif isinstance(value, bytes):
                    value = f"<BLOB {len(value)} bytes>"
                else:
                    value = str(value)

                value = value.replace("\r", "\\r")
                value = value.replace("\n", "\\n")

                values.append(value)

            f.write(
                f"[{row_number}] " +
                " | ".join(values) +
                "\n"
            )

con.close()

print("=" * 70)
print("EXTRACTION SUCCESS")
print("=" * 70)
print(f"عدد الجداول: {len(tables)}")
print(f"الملف: {OUT.resolve()}")
print("قاعدة البيانات: لم يتم تعديلها")
print("STATUS: SUCCESS")
print("=" * 70)
