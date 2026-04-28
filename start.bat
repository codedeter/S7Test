@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PYTHONPATH=%SCRIPT_DIR%;%PYTHONPATH%"

python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found. Please install Python 3.8 or higher.
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

if not exist "venv\Scripts\activate.bat" (
    echo Info: Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Error: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo Success: Virtual environment created
)

echo Info: Activating virtual environment...
call venv\Scripts\activate.bat

echo Info: Checking dependencies...
pip install -r requirements.txt >nul 2>&1
if errorlevel 1 (
    echo Info: Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo Error: Failed to install dependencies
        pause
        exit /b 1
    )
)

echo.
echo ========================================
echo    PLC Data Monitoring System
echo ========================================
echo.
echo Access: http://localhost:3000
echo Press Ctrl+C to stop
echo.

python src\server.py

if errorlevel 1 (
    echo.
    echo Error: Server failed to start
    pause
)

endlocal