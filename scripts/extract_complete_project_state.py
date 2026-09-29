from pathlib import Path
from datetime import datetime
import sqlite3
import subprocess
import sys
import hashlib
import os

ROOT = Path.cwd()
OUT = ROOT / "PROJECT_CONTINUATION_PACKAGE.txt"

EXCLUDE_DIRS = {
    ".venv",
    "__pycache__",
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
}

TEXT_EXTENSIONS = {
    ".py",".pyw",".txt",".md",".json",".yaml",".yml",".toml",
    ".ini",".cfg",".conf",".sql",".xml",".html",".css",".js",
    ".ts",".tsx",".bat",".cmd",".ps1",".sh",".env",".properties"
}

SKIP_BINARY_EXTENSIONS = {
    ".db-wal",".db-shm",".exe",".dll",".pyd",".so",
    ".png",".jpg",".jpeg",".gif",".webp",".ico",
    ".pdf",".xlsx",".xls",".docx",".pptx",".zip",".7z",".rar"
}

lines = []

def out(s=""):
    lines.append(str(s))

def section(title):
    out("")
    out("=" * 100)
    out(title)
    out("=" * 100)

def sha256_file(path):
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                h.update(block)
        return h.hexdigest()
    except Exception as e:
        return f"HASH_ERROR:{e}"

def safe_text(path):
    try:
        return path.read_text(encoding="utf-8-sig")
    except Exception:
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return f"[READ_ERROR: {e}]"

out("PROJECT CONTINUATION PACKAGE")
out(f"Generated: {datetime.now().isoformat()}")
out(f"Root: {ROOT}")
out(f"Python: {sys.executable}")
out(f"Python version: {sys.version}")

# ============================================================
# PROJECT TREE + FILE INVENTORY
# ============================================================
section("1. COMPLETE PROJECT FILE INVENTORY")

files = []

for p in ROOT.rglob("*"):
    if not p.is_file():
        continue

    rel = p.relative_to(ROOT)
    parts = set(rel.parts)

    if parts & EXCLUDE_DIRS:
        continue

    if p.name == OUT.name:
        continue

    files.append(p)

files.sort(key=lambda x: str(x.relative_to(ROOT)).lower())

out(f"FILE_COUNT_EXCLUDING_BUILD_CACHE={len(files)}")

for p in files:
    rel = p.relative_to(ROOT)
    try:
        stat = p.stat()
        size = stat.st_size
    except Exception:
        size = -1

    out(
        f"{rel} | SIZE={size} | SHA256={sha256_file(p)}"
    )

# ============================================================
# DIRECTORY TREE
# ============================================================
section("2. DIRECTORY TREE")

dirs = set()

for p in files:
    rel = p.relative_to(ROOT)
    current = ROOT
    for part in rel.parts[:-1]:
        current = current / part
        dirs.add(current.relative_to(ROOT))

for d in sorted(dirs, key=lambda x: str(x).lower()):
    out(str(d))

# ============================================================
# PYTHON ENVIRONMENT
# ============================================================
section("3. PYTHON ENVIRONMENT")

try:
    p = subprocess.run(
        [sys.executable, "--version"],
        capture_output=True,
        text=True
    )
    out(p.stdout.strip() or p.stderr.strip())
except Exception as e:
    out(f"PYTHON_VERSION_ERROR={e}")

try:
    p = subprocess.run(
        [sys.executable, "-m", "pip", "list"],
        capture_output=True,
        text=True
    )
    out(p.stdout)
except Exception as e:
    out(f"PIP_LIST_ERROR={e}")

# ============================================================
# GIT
# ============================================================
section("4. GIT STATUS")

if (ROOT / ".git").exists():
    try:
        p = subprocess.run(
            ["git", "status", "--short"],
            cwd=ROOT,
            capture_output=True,
            text=True
        )
        out("GIT STATUS:")
        out(p.stdout or "(clean)")
    except Exception as e:
        out(f"GIT_STATUS_ERROR={e}")

    try:
        p = subprocess.run(
            ["git", "log", "-10", "--oneline"],
            cwd=ROOT,
            capture_output=True,
            text=True
        )
        out("GIT LOG:")
        out(p.stdout)
    except Exception as e:
        out(f"GIT_LOG_ERROR={e}")
else:
    out("GIT_REPOSITORY=NOT_PRESENT")

# ============================================================
# DATABASE DISCOVERY
# ============================================================
section("5. DATABASE DISCOVERY")

db_candidates = sorted(ROOT.rglob("*.db"))

for db in db_candidates:
    if any(part in EXCLUDE_DIRS for part in db.relative_to(ROOT).parts):
        continue

    out(f"DATABASE={db.relative_to(ROOT)}")
    out(f"SIZE={db.stat().st_size}")
    out(f"SHA256={sha256_file(db)}")

    try:
        con = sqlite3.connect(str(db))
        con.row_factory = sqlite3.Row

        integrity = con.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        fk = con.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        out(f"INTEGRITY_CHECK={integrity}")
        out(f"FOREIGN_KEY_ERRORS={len(fk)}")

        # ----------------------------------------------------
        # SQLite schema
        # ----------------------------------------------------
        section(f"SCHEMA: {db.relative_to(ROOT)}")

        tables = con.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type='table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """).fetchall()

        out(f"TABLE_COUNT={len(tables)}")

        for row in tables:
            table = row[0]

            out("")
            out(f"TABLE={table}")

            cols = con.execute(
                f'PRAGMA table_info("{table}")'
            ).fetchall()

            for c in cols:
                out(
                    f"COLUMN | name={c['name']} | type={c['type']} "
                    f"| notnull={c['notnull']} | default={c['dflt_value']} "
                    f"| pk={c['pk']}"
                )

            fks = con.execute(
                f'PRAGMA foreign_key_list("{table}")'
            ).fetchall()

            for fkrow in fks:
                out(
                    f"FOREIGN_KEY | from={fkrow['from']} "
                    f"| to_table={fkrow['table']} "
                    f"| to_column={fkrow['to']}"
                )

            indexes = con.execute(
                f'PRAGMA index_list("{table}")'
            ).fetchall()

            for idx in indexes:
                out(
                    f"INDEX | name={idx['name']} "
                    f"| unique={idx['unique']}"
                )

            try:
                count = con.execute(
                    f'SELECT COUNT(*) FROM "{table}"'
                ).fetchone()[0]

                out(f"ROW_COUNT={count}")
            except Exception as e:
                out(f"ROW_COUNT_ERROR={e}")

        # ----------------------------------------------------
        # Triggers
        # ----------------------------------------------------
        section(f"TRIGGERS: {db.relative_to(ROOT)}")

        triggers = con.execute("""
            SELECT name, sql
            FROM sqlite_master
            WHERE type='trigger'
            ORDER BY name
        """).fetchall()

        out(f"TRIGGER_COUNT={len(triggers)}")

        for t in triggers:
            out(f"TRIGGER={t['name']}")
            out(t["sql"] or "")

        # ----------------------------------------------------
        # Views
        # ----------------------------------------------------
        section(f"VIEWS: {db.relative_to(ROOT)}")

        views = con.execute("""
            SELECT name, sql
            FROM sqlite_master
            WHERE type='view'
            ORDER BY name
        """).fetchall()

        out(f"VIEW_COUNT={len(views)}")

        for v in views:
            out(f"VIEW={v['name']}")
            out(v["sql"] or "")

        con.close()

    except Exception as e:
        out(f"DATABASE_AUDIT_ERROR={repr(e)}")

# ============================================================
# IMPORTANT TEXT FILE CONTENT
# ============================================================
section("6. COMPLETE TEXT SOURCE CONTENT")

for p in files:
    rel = p.relative_to(ROOT)

    if p.suffix.lower() not in TEXT_EXTENSIONS:
        continue

    # Avoid dumping gigantic generated reports more than needed.
    # All filenames/hashes remain in section 1.
    try:
        size = p.stat().st_size
    except Exception:
        continue

    if size > 2_000_000:
        out("")
        out("#" * 100)
        out(f"FILE={rel}")
        out(f"CONTENT_SKIPPED_SIZE={size}")
        out("FILE_IS_TOO_LARGE_FOR_SINGLE_TEXT_PACKAGE")
        out("#" * 100)
        continue

    out("")
    out("#" * 100)
    out(f"FILE={rel}")
    out(f"SIZE={size}")
    out(f"SHA256={sha256_file(p)}")
    out("#" * 100)

    out(safe_text(p))

# ============================================================
# IMPORTANT CURRENT FILES HIGHLIGHT
# ============================================================
section("7. CURRENT CORE FILES")

important = [
    "app/ui/main_window.py",
    "app/ui/pos_window.py",
    "app/services/inventory_service.py",
    "app/services/erp_engine.py",
    "app/services/pos_service.py",
    "app/services/pos_search_service.py",
    "app/database/connection.py",
    "app/core/config.py",
    "requirements.txt",
    "pyproject.toml",
    "README.md",
]

for rel in important:
    p = ROOT / rel
    if p.exists():
        out(f"CORE_FILE_EXISTS={rel}")
        out(f"SIZE={p.stat().st_size}")
        out(f"SHA256={sha256_file(p)}")
    else:
        out(f"CORE_FILE_MISSING={rel}")

# ============================================================
# RECENT REPORTS
# ============================================================
section("8. RECENT REPORTS")

reports = ROOT / "reports"

if reports.exists():
    recent = sorted(
        [p for p in reports.rglob("*") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    for p in recent[:100]:
        out(
            f"{p.relative_to(ROOT)} | "
            f"SIZE={p.stat().st_size} | "
            f"MODIFIED={datetime.fromtimestamp(p.stat().st_mtime).isoformat()}"
        )
else:
    out("REPORTS_DIRECTORY_MISSING")

# ============================================================
# RECENT BACKUPS
# ============================================================
section("9. RECENT BACKUPS")

backups = ROOT / "backups"

if backups.exists():
    recent = sorted(
        [p for p in backups.rglob("*") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    for p in recent[:150]:
        out(
            f"{p.relative_to(ROOT)} | "
            f"SIZE={p.stat().st_size} | "
            f"MODIFIED={datetime.fromtimestamp(p.stat().st_mtime).isoformat()}"
        )
else:
    out("BACKUPS_DIRECTORY_MISSING")

# ============================================================
# MASTER AUDIT
# ============================================================
section("10. MASTER AUDIT REFERENCE")

master = ROOT / "PROJECT_MASTER_AUDIT.txt"

if master.exists():
    out(f"MASTER_AUDIT_SIZE={master.stat().st_size}")
    out(f"MASTER_AUDIT_SHA256={sha256_file(master)}")
    out("")
    out(safe_text(master))
else:
    out("PROJECT_MASTER_AUDIT.txt NOT FOUND")

# ============================================================
# FINAL
# ============================================================
section("11. CONTINUATION INSTRUCTIONS")

out("This package is a technical snapshot of the project.")
out("Use the latest generated package as the primary continuation reference.")
out("Do not delete or merge database tables based only on names.")
out("Do not change currency, country, timezone, or tax configuration without explicit confirmation.")
out("Do not treat BOM alone as a Python syntax failure.")
out("The project should be repaired in controlled stages.")
out("")

OUT.write_text("\n".join(lines), encoding="utf-8")

print("=" * 70)
print("PROJECT EXTRACTION COMPLETE")
print("=" * 70)
print(f"FILE: {OUT}")
print(f"SIZE: {OUT.stat().st_size} bytes")
print(f"LINES: {len(lines)}")
print("=" * 70)
