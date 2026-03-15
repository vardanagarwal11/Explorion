@echo off
echo =======================================================
echo Starting Explorion Backend API Server...
echo =======================================================
echo.

if "%VIRTUAL_ENV%"=="" (
    echo [WARNING] No virtual environment detected!
    echo Checking for "venv" folder...
    
    if exist "venv\Scripts\activate.bat" (
        echo Activating virtual environment...
        call venv\Scripts\activate.bat
    ) else (
        echo [ERROR] Virtual environment "venv" not found.
        echo Please create a virtual environment and install requirements first.
        exit /b 1
    )
)

echo [OK] Virtual environment active: %VIRTUAL_ENV%
echo.

python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
