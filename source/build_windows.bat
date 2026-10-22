@echo off
setlocal
cd /d "%~dp0"
py -m pip install --upgrade pip
if errorlevel 1 exit /b 1
py -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
py -m PyInstaller --noconfirm --clean TDE_CONTROL_CENTER_v1.0.spec
if errorlevel 1 exit /b 1
for /f "delims=" %%V in ('py -c "from app.version import EXE_NAME; print(EXE_NAME)"') do set "TDE_EXE_NAME=%%V"
if not defined TDE_EXE_NAME exit /b 1
if not exist "dist\%TDE_EXE_NAME%.exe" exit /b 1
echo.
echo EXE: dist\%TDE_EXE_NAME%.exe
endlocal
