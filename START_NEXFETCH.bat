@echo off
cd /d "%~dp0"
:: Check Python silently
python --version >nul 2>&1
if %errorlevel% neq 0 (
    msg * "Python not found. Install from python.org and tick Add to PATH" >nul 2>&1
    start https://www.python.org/downloads/
    exit /b 1
)
:: Launch via VBS so NO cmd window appears at all
cscript //nologo "%~dp0START_SILENT.vbs"
