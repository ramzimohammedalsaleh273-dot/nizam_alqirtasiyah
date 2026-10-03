$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

Write-Host "نظام القرطاسية - بناء إصدار Windows"

$python = Join-Path (Get-Location) ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

& $python -m pip install --disable-pip-version-check pyinstaller
if ($LASTEXITCODE -ne 0) { throw "تعذر تثبيت PyInstaller" }

if (Test-Path ".\build") { Remove-Item ".\build" -Recurse -Force }
if (Test-Path ".\dist\NizamAlQirtasiyah") { Remove-Item ".\dist\NizamAlQirtasiyah" -Recurse -Force }

& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --onedir `
    --name "NizamAlQirtasiyah" `
    --paths "." `
    --collect-all PySide6 `
    --collect-all reportlab `
    "main.py"

if ($LASTEXITCODE -ne 0) { throw "فشل بناء تطبيق سطح المكتب" }

$release = Join-Path (Get-Location) "dist\NizamAlQirtasiyah"
if (-not (Test-Path (Join-Path $release "NizamAlQirtasiyah.exe"))) {
    throw "ملف التطبيق التنفيذي لم يُنشأ"
}

Write-Host "تم بناء إصدار Windows في: $release"
Write-Host "التشغيل: .\dist\NizamAlQirtasiyah\NizamAlQirtasiyah.exe"
