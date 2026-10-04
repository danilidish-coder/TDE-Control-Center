@echo off
setlocal
cd /d "%~dp0"
py -m pip install --upgrade pip
if errorlevel 1 exit /b 1
py -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
py -m PyInstaller --noconfirm --clean TDE_CONTROL_CENTER_v1.0.spec
if errorlevel 1 exit /b 1
if not exist "dist\TDE_CONTROL_CENTER_v1.0.exe" exit /b 1
echo.
echo EXE: dist\TDE_CONTROL_CENTER_v1.0.exe
endlocal
