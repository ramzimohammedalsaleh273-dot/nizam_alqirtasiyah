from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys

ROOT = Path.cwd()
APP = ROOT / "app"
MAIN = APP / "ui" / "main_window.py"
BACKUPS = ROOT / "backups"
REPORTS = ROOT / "reports"

BACKUPS.mkdir(exist_ok=True)
REPORTS.mkdir(exist_ok=True)

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
report = REPORTS / f"stage_01_runtime_encoding_{stamp}.txt"

lines = []
def log(x=""):
    print(x)
    lines.append(str(x))

log("=" * 70)
log("STAGE 01 - RUNTIME + SAFE ENCODING VERIFICATION")
log("=" * 70)
log(f"ROOT: {ROOT}")
log(f"PYTHON: {sys.executable}")
log(f"PYTHON VERSION: {sys.version}")

if not MAIN.exists():
    raise SystemExit(f"MAIN WINDOW MISSING: {MAIN}")

# ------------------------------------------------------------
# 1. Backup current main window before any modification
# ------------------------------------------------------------
backup = BACKUPS / f"before_stage_01_main_window_{stamp}.py"
shutil.copy2(MAIN, backup)
log(f"BACKUP: {backup}")

# ------------------------------------------------------------
# 2. Read exact bytes safely
# ------------------------------------------------------------
raw = MAIN.read_bytes()
has_bom = raw.startswith(b"\xef\xbb\xbf")

try:
    text = raw.decode("utf-8-sig")
    decode_status = "UTF-8/UTF-8-BOM READABLE"
except Exception as e:
    log(f"UTF-8 READ ERROR: {e}")
    raise

log(f"MAIN BYTES: {len(raw)}")
log(f"UTF8 BOM: {has_bom}")
log(f"MAIN DECODE: {decode_status}")

# ------------------------------------------------------------
# 3. Verify run() and __main__ guard
# ------------------------------------------------------------
has_run = "def run(" in text
has_guard = 'if __name__ == "__main__":' in text

log(f"RUN FUNCTION: {has_run}")
log(f"MAIN GUARD: {has_guard}")

if not has_run:
    raise SystemExit("ERROR: def run() was not found; file was NOT changed.")

# Add ONLY the missing main guard.
# Do not rewrite the file or alter its existing application logic.
if not has_guard:
    addition = '\n\nif __name__ == "__main__":\n    run()\n'
    text = text.rstrip() + addition
    MAIN.write_text(text, encoding="utf-8")
    log("MAIN GUARD: ADDED")
else:
    log("MAIN GUARD: ALREADY PRESENT")

# ------------------------------------------------------------
# 4. Python compilation test for the main window
# ------------------------------------------------------------
compile_cmd = [
    sys.executable,
    "-m",
    "py_compile",
    str(MAIN)
]

p = subprocess.run(
    compile_cmd,
    cwd=str(ROOT),
    capture_output=True,
    text=True
)

log(f"MAIN PY_COMPILE EXIT: {p.returncode}")

if p.stdout.strip():
    log("PY_COMPILE STDOUT:")
    log(p.stdout.strip())

if p.stderr.strip():
    log("PY_COMPILE STDERR:")
    log(p.stderr.strip())

if p.returncode != 0:
    log("RESULT: MAIN WINDOW COMPILATION FAILED")
else:
    log("RESULT: MAIN WINDOW COMPILATION OK")

# ------------------------------------------------------------
# 5. Verify Python files without treating BOM as a syntax error
# ------------------------------------------------------------
py_files = sorted(APP.rglob("*.py"))
ok = 0
failed = 0
bom_count = 0
errors = []

for f in py_files:
    try:
        b = f.read_bytes()
        if b.startswith(b"\xef\xbb\xbf"):
            bom_count += 1

        compile(b, str(f), "exec")
        ok += 1
    except Exception as e:
        failed += 1
        errors.append((str(f.relative_to(ROOT)), repr(e)))

log("")
log("=" * 70)
log("PYTHON SOURCE VERIFICATION")
log("=" * 70)
log(f"PYTHON FILES: {len(py_files)}")
log(f"COMPILE OK: {ok}")
log(f"COMPILE FAILED: {failed}")
log(f"FILES WITH UTF8 BOM: {bom_count}")

if errors:
    log("")
    log("REAL COMPILE ERRORS:")
    for name, err in errors:
        log(f"{name} -> {err}")

# ------------------------------------------------------------
# 6. Import test
# ------------------------------------------------------------
env = dict(__import__("os").environ)
env["PYTHONPATH"] = str(ROOT)

import_test = subprocess.run(
    [
        sys.executable,
        "-c",
        "import app.ui.main_window; print('IMPORT_MAIN_WINDOW_OK')"
    ],
    cwd=str(ROOT),
    env=env,
    capture_output=True,
    text=True
)

log("")
log("=" * 70)
log("IMPORT TEST")
log("=" * 70)
log(f"IMPORT EXIT: {import_test.returncode}")

if import_test.stdout.strip():
    log(import_test.stdout.strip())

if import_test.stderr.strip():
    log(import_test.stderr.strip())

# ------------------------------------------------------------
# 7. Database integrity check - READ ONLY
# ------------------------------------------------------------
db_candidates = [
    ROOT / "database" / "nizam_alqirtasiyah.db",
    ROOT / "data" / "nizam_alqirtasiyah.db",
]

db = next((x for x in db_candidates if x.exists()), None)

if db:
    import sqlite3

    con = sqlite3.connect(db)
    try:
        integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = con.execute("PRAGMA foreign_key_check").fetchall()

        log("")
        log("=" * 70)
        log("DATABASE READ-ONLY CHECK")
        log("=" * 70)
        log(f"DB: {db}")
        log(f"INTEGRITY: {integrity}")
        log(f"FOREIGN KEY ERRORS: {len(foreign_keys)}")
    finally:
        con.close()
else:
    log("DATABASE: NOT FOUND")

# ------------------------------------------------------------
# 8. Final result
# ------------------------------------------------------------
if p.returncode == 0 and import_test.returncode == 0 and failed == 0:
    status = "STAGE 01 SUCCESS"
else:
    status = "STAGE 01 COMPLETED WITH ERRORS - DO NOT CONTINUE AUTOMATICALLY"

log("")
log("=" * 70)
log(status)
log("=" * 70)

report.write_text("\n".join(lines) + "\n", encoding="utf-8")
log(f"REPORT: {report}")

print("")
print("STAGE 01 FINISHED")
print(f"REPORT: {report}")
print(f"STATUS: {status}")
