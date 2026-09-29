$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path ".venv\Scripts\python.exe"){$env:PYTHONPATH=(Get-Location).Path;& ".\.venv\Scripts\python.exe" -m app.ui.main_window}else{Write-Host "لم يتم العثور على .venv" -ForegroundColor Yellow;exit 1}
