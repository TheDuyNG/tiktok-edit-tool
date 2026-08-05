@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_HOME=%LocalAppData%\Programs\Python\Python312"
set "PYTHON_EXE=%PYTHON_HOME%\pythonw.exe"
set "PYTHON_CONSOLE=%PYTHON_HOME%\python.exe"
set "CUDA_SITE=%LocalAppData%\SRT_MAKER\cuda_site"
set "OLD_SITE_PACKAGES=%CD%\.venv\Lib\site-packages"

if not exist "%PYTHON_EXE%" goto :missing_python
if not exist "%OLD_SITE_PACKAGES%" goto :missing_libraries

if exist "%CUDA_SITE%" (
    set "PYTHONPATH=%CUDA_SITE%;%OLD_SITE_PACKAGES%"
) else (
    set "PYTHONPATH=%OLD_SITE_PACKAGES%"
)
"%PYTHON_CONSOLE%" -c "import tkinter as tk, pysrt; root=tk.Tk(); root.withdraw(); root.update_idletasks(); root.destroy()" >nul 2>&1
if errorlevel 1 goto :import_error

start "SRT Maker" "%PYTHON_EXE%" "%CD%\main.py"
exit /b 0

:missing_python
echo Khong tim thay Python hoat dong tai:
echo %PYTHON_EXE%
echo.
echo Hay cai Python 3.12 kem Tcl/Tk.
pause
exit /b 1

:missing_libraries
echo Khong tim thay thu vien cua du an tai:
echo %OLD_SITE_PACKAGES%
pause
exit /b 1

:import_error
echo Khong nap duoc thu vien cua SRT Maker.
echo Dang chay lai de hien thi loi chi tiet...
echo.
"%PYTHON_CONSOLE%" -c "import tkinter as tk, pysrt, main; root=tk.Tk(); root.destroy()"
pause
exit /b 1
