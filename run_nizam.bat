@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (set PYTHONPATH=%CD%& ".venv\Scripts\python.exe" -m app.ui.main_window) else (echo لم يتم العثور على البيئة الافتراضية .venv&pause)
