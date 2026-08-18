@echo off
setlocal
cd /d "%~dp0"
py -3 --version >nul 2>&1
if errorlevel 1 (
    echo Python 3.10+ is required and was not found in PATH.
    echo Please install Python from https://python.org and reopen this installer.
    pause
    exit /b 1
)

py -3 -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo.
echo Setup complete. Run run_app.bat to launch the app.
pause
