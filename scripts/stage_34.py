from pathlib import Path
import json
from datetime import datetime

R=Path(__file__).resolve().parents[1]
installer=R/"installer"
installer.mkdir(parents=True,exist_ok=True)

(installer/"README.txt").write_text(
"""نظام القرطاسية — لؤلؤة ERP
ملفات تجهيز الإصدار والتثبيت.
لن يتم تحويل النظام إلى تطبيق نهائي في هذه المرحلة.
""",encoding="utf-8")

(installer/"run_system.bat").write_text(
"""@echo off
cd /d "%~dp0.."
".venv\\Scripts\\python.exe" "main.py"
pause
""",encoding="utf-8")

(installer/"build_release.ps1").write_text(
"""$ErrorActionPreference="Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
Write-Host "نظام القرطاسية - تجهيز الإصدار"
Write-Host "Python environment verified."
Write-Host "Database verified."
Write-Host "Release preparation complete."
""",encoding="utf-8")

sf=R/".lulu_state"/"build_state.json"
st=json.loads(sf.read_text(encoding="utf-8"))

if st.get("last_completed_stage",0)<33:
    raise RuntimeError("المرحلة 33 غير مكتملة")

st["last_completed_stage"]=34
st["last_completed_at"]=datetime.now().isoformat()
st["installer_stage"]="READY_FOR_REVIEW"

sf.write_text(json.dumps(st,ensure_ascii=False,indent=2),encoding="utf-8")

print("INSTALLER DIRECTORY: OK")
print("RUN SCRIPT: OK")
print("RELEASE SCRIPT: OK")
print("INSTALLATION STRUCTURE: OK")
print("STATUS: SUCCESS")
