@echo off
title NexFetch DEBUG
color 0E
cd /d "%~dp0"
echo NexFetch DEBUG — errors shown here
echo ------------------------------------------------
python --version >nul 2>&1
if %errorlevel% neq 0 (echo Python not found! & pause & exit /b 1)
python NexFetch.py
echo ------------------------------------------------
echo Exited. Copy any error above for support.
pause
