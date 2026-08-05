@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

if not exist ".venv\Scripts\python.exe" (
    echo [LOI] Khong tim thay Python 3.12 trong .venv.
    echo Hay cai thu vien truoc khi chay AUTOTTS.
    pause
    exit /b 1
)

if not exist "TTS_v2_5_UI_Pro.py" (
    echo [LOI] Khong tim thay TTS_v2_5_UI_Pro.py.
    pause
    exit /b 1
)

start "AUTOTTS PRO" ".venv\Scripts\python.exe" "TTS_v2_5_UI_Pro.py"
exit /b 0
