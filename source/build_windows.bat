@echo off
setlocal
cd /d "%~dp0"
python -m PyInstaller --clean --noconfirm TDE_Control_Center.spec
if errorlevel 1 exit /b 1
exit /b 0
