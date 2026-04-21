@echo off
title NexFetch - Build EXE
cd /d "%~dp0"
echo.
echo  NexFetch - Build Standalone EXE
echo  ================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found. Install from python.org (Add to PATH)
    pause & exit /b 1
)

echo [1/4] Installing PyInstaller + Pillow...
python -m pip install pyinstaller pillow --quiet --upgrade

echo [2/4] Converting logo...
if exist "assets\logo.png" (
    python -c "from PIL import Image; img=Image.open('assets/logo.png').convert('RGBA'); img.save('assets/logo.ico',format='ICO',sizes=[(256,256),(128,128),(64,64),(32,32),(16,16)])" >nul 2>&1
    if exist "assets\logo.ico" echo  Logo converted to ICO.
)

set ICON_ARG=
if exist "assets\logo.ico" set ICON_ARG=--icon=assets\logo.ico

echo [3/4] Building EXE...
python -m PyInstaller ^
    --name "NexFetch" ^
    --windowed ^
    --onedir ^
    --distpath "NexFetch_EXE" ^
    --workpath "build_tmp" ^
    --noconfirm ^
    --clean ^
    --noupx ^
    %ICON_ARG% ^
    --add-data "core;core" ^
    --add-data "assets;assets" ^
    --hidden-import instaloader ^
    --hidden-import PIL ^
    --hidden-import PIL.Image ^
    --hidden-import PIL.ImageTk ^
    --hidden-import tkinter ^
    --hidden-import tkinter.ttk ^
    --hidden-import tkinter.scrolledtext ^
    --hidden-import tkinter.colorchooser ^
    --hidden-import bs4 ^
    --hidden-import lxml ^
    NexFetch.py

if %errorlevel% neq 0 (
    echo BUILD FAILED. Run START_DEBUG.bat to see the error.
    pause & exit /b 1
)

echo [4/4] Copying runtime files...
if exist "ffmpeg_bin"   xcopy /E /I /Y "ffmpeg_bin"  "NexFetch_EXE\NexFetch\ffmpeg_bin"  >nul 2>&1
if exist "users.json"   copy  /Y       "users.json"   "NexFetch_EXE\NexFetch\users.json"  >nul 2>&1
if exist "config.json"  copy  /Y       "config.json"  "NexFetch_EXE\NexFetch\config.json" >nul 2>&1
if exist "saved_logins.json" copy /Y "saved_logins.json" "NexFetch_EXE\NexFetch\saved_logins.json" >nul 2>&1
if exist "userdata"     xcopy /E /I /Y "userdata"     "NexFetch_EXE\NexFetch\userdata"    >nul 2>&1
if exist "assets"       xcopy /E /I /Y "assets"       "NexFetch_EXE\NexFetch\assets"      >nul 2>&1
for %%f in (.ig_session_*) do copy /Y "%%f" "NexFetch_EXE\NexFetch\%%f" >nul 2>&1
echo ok > "NexFetch_EXE\NexFetch\.setup_complete"

if exist "build_tmp" rd /s /q "build_tmp" >nul 2>&1
if exist "NexFetch.spec" del /f "NexFetch.spec" >nul 2>&1

echo.
echo  ================================
echo  BUILD COMPLETE!
echo  EXE is at: NexFetch_EXE\NexFetch\NexFetch.exe
echo.
echo  To install as a proper app:
echo  1. Open NexFetch_EXE\NexFetch\
echo  2. Right-click NexFetch.exe
echo  3. Send to > Desktop (shortcut)
echo  4. Right-click shortcut > Pin to taskbar
echo  ================================
pause
