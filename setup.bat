@echo off
setlocal EnableDelayedExpansion

:: =============================================================
:: Explorion Project Setup Script (Windows)
:: =============================================================
:: Requirements: Node.js 18+, npm, Python 3.8+, pip, Docker Desktop
:: Run from the project root (where backend\ and frontend\ exist)
:: =============================================================

title Explorion Setup

echo ========================================
echo    Setting up Explorion Project
echo ========================================
echo.

:: -------------------------------------------------------
:: Check we are in the right directory
:: -------------------------------------------------------
if not exist "backend\" (
    call :log_error "backend\ folder not found."
    call :log_error "Please run this script from the project root."
    goto :fail
)
if not exist "frontend\" (
    call :log_error "frontend\ folder not found."
    call :log_error "Please run this script from the project root."
    goto :fail
)

:: -------------------------------------------------------
:: Detect Node.js
:: -------------------------------------------------------
call :log_info "Checking Node.js..."
where node >nul 2>&1
if errorlevel 1 (
    call :log_error "Node.js is not installed or not on PATH."
    call :log_error "Download from https://nodejs.org and re-run this script."
    goto :fail
)

for /f "tokens=* usebackq" %%v in (`node -v 2^>nul`) do set NODE_VER=%%v
set NODE_VER=%NODE_VER:v=%
for /f "tokens=1 delims=." %%m in ("%NODE_VER%") do set NODE_MAJOR=%%m
if %NODE_MAJOR% LSS 18 (
    call :log_error "Node.js 18+ required. Current: v%NODE_VER%"
    call :log_error "Please upgrade Node.js from https://nodejs.org"
    goto :fail
)
call :log_success "Node.js v%NODE_VER% detected."

:: -------------------------------------------------------
:: Detect npm
:: -------------------------------------------------------
where npm >nul 2>&1
if errorlevel 1 (
    call :log_error "npm not found. Reinstall Node.js from https://nodejs.org"
    goto :fail
)
for /f "tokens=* usebackq" %%v in (`npm -v 2^>nul`) do set NPM_VER=%%v
call :log_success "npm %NPM_VER% detected."

:: -------------------------------------------------------
:: Detect Python 3.8+
:: -------------------------------------------------------
call :log_info "Checking Python..."
set PYTHON_CMD=
set PIP_CMD=

:: Try each candidate in order
for %%c in (python3 python py) do (
    if "!PYTHON_CMD!"=="" (
        where %%c >nul 2>&1
        if not errorlevel 1 (
            :: Verify version
            for /f "tokens=* usebackq" %%v in (`%%c -c "import sys; print('%%d.%%d' %% sys.version_info[:2])" 2^>nul`) do set PY_VER=%%v
            if not "!PY_VER!"=="" (
                for /f "tokens=1 delims=." %%a in ("!PY_VER!") do set PY_MAJOR=%%a
                for /f "tokens=2 delims=." %%b in ("!PY_VER!") do set PY_MINOR=%%b
                if !PY_MAJOR! GEQ 3 (
                    if !PY_MINOR! GEQ 8 (
                        set PYTHON_CMD=%%c
                    )
                )
            )
        )
    )
)

if "!PYTHON_CMD!"=="" (
    call :log_error "Python 3.8+ not found on PATH."
    call :log_error "Download from https://www.python.org/downloads/"
    call :log_error "Make sure to check 'Add Python to PATH' during installation."
    goto :fail
)
call :log_success "Python %PY_VER% detected (!PYTHON_CMD!)."

:: Detect pip
set PIP_CMD=
for %%p in (pip3 pip) do (
    if "!PIP_CMD!"=="" (
        where %%p >nul 2>&1
        if not errorlevel 1 set PIP_CMD=%%p
    )
)
if "!PIP_CMD!"=="" (
    !PYTHON_CMD! -m pip --version >nul 2>&1
    if not errorlevel 1 (
        set PIP_CMD=!PYTHON_CMD! -m pip
    ) else (
        call :log_error "pip not found. Please install pip for !PYTHON_CMD!."
        goto :fail
    )
)
call :log_success "pip detected (!PIP_CMD!)."

:: -------------------------------------------------------
:: Detect Docker (optional)
:: -------------------------------------------------------
set DOCKER_AVAILABLE=false
set COMPOSE_AVAILABLE=false

where docker >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=* usebackq" %%v in (`docker --version 2^>nul`) do set DOCKER_VER=%%v
    call :log_success "Docker detected: !DOCKER_VER!"
    set DOCKER_AVAILABLE=true

    docker-compose --version >nul 2>&1
    if not errorlevel 1 (
        set COMPOSE_AVAILABLE=true
        call :log_success "Docker Compose (standalone) detected."
    ) else (
        docker compose version >nul 2>&1
        if not errorlevel 1 (
            set COMPOSE_AVAILABLE=true
            call :log_success "Docker Compose (plugin) detected."
        ) else (
            call :log_warning "Docker Compose not found. Manual start still works."
        )
    )
) else (
    call :log_warning "Docker not found. You can still run the app manually."
)

echo.
:: -------------------------------------------------------
:: Backend setup
:: -------------------------------------------------------
call :log_info "Setting up backend..."
cd backend

:: .env
if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        call :log_success "Created backend\.env from .env.example"
        call :log_warning "Please edit backend\.env with your actual API keys."
    ) else (
        call :log_warning ".env.example not found — skipping .env creation."
    )
) else (
    call :log_info "backend\.env already exists — skipping."
)

:: Sanity-check existing venv
if exist "venv\" (
    venv\Scripts\python.exe -c "import sys" >nul 2>&1
    if errorlevel 1 (
        call :log_warning "Existing venv appears broken — removing and recreating..."
        rmdir /s /q venv
    ) else (
        call :log_info "Existing virtual environment found."
    )
)

:: Create venv if missing
if not exist "venv\" (
    call :log_info "Creating Python virtual environment..."
    !PYTHON_CMD! -m venv venv
    if errorlevel 1 (
        call :log_error "Failed to create virtual environment."
        call :log_error "Try: !PYTHON_CMD! -m pip install virtualenv"
        cd ..
        goto :fail
    )
    call :log_success "Virtual environment created."
)

:: Activate venv — on Windows we use the Scripts\activate.bat
if not exist "venv\Scripts\activate.bat" (
    call :log_error "venv\Scripts\activate.bat not found. The venv may be corrupted."
    call :log_error "Delete the venv\ folder and re-run this script."
    cd ..
    goto :fail
)

call venv\Scripts\activate.bat
if errorlevel 1 (
    call :log_error "Failed to activate virtual environment."
    cd ..
    goto :fail
)
call :log_success "Virtual environment activated."

:: Upgrade pip inside venv
call :log_info "Upgrading pip inside venv..."
python -m pip install --upgrade pip >nul 2>&1
if errorlevel 1 call :log_warning "pip upgrade failed — continuing."

:: Install Python deps
if not exist "requirements.txt" (
    call :log_warning "requirements.txt not found — skipping dependency install."
) else (
    call :log_info "Installing Python dependencies..."
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        call :log_error "Failed to install Python dependencies."
        call :log_error "Check requirements.txt for errors."
        cd ..
        goto :fail
    )
)

call :log_success "Backend setup complete!"
cd ..

echo.
:: -------------------------------------------------------
:: Frontend setup
:: -------------------------------------------------------
call :log_info "Setting up frontend..."
cd frontend

call :log_info "Installing Node.js dependencies..."
npm install
if errorlevel 1 (
    call :log_error "npm install failed."
    call :log_error "Try deleting node_modules\ and re-running."
    cd ..
    goto :fail
)

call :log_success "Frontend setup complete!"
cd ..

:: -------------------------------------------------------
:: Done
:: -------------------------------------------------------
echo.
echo ========================================
call :log_success "Setup complete!"
echo.
echo Next steps:
echo   1. Edit backend\.env with your API keys (if not done already)
echo.
echo   Manual start:
echo     Terminal 1 (backend):
echo       cd backend
echo       venv\Scripts\activate
echo       python main.py
echo.
echo     Terminal 2 (frontend):
echo       cd frontend
echo       npm run dev
echo.
if "%COMPOSE_AVAILABLE%"=="true" (
    echo   Docker start:
    echo       docker-compose up --build
    echo.
)
call :log_info "Happy coding!"
echo ========================================
goto :end

:: -------------------------------------------------------
:: :fail  — clean exit on error
:: -------------------------------------------------------
:fail
echo.
echo ========================================
call :log_error "Setup failed. Review the messages above and try again."
echo ========================================
endlocal
exit /b 1

:: -------------------------------------------------------
:: Logging helpers
:: -------------------------------------------------------
:log_info
echo [INFO] %~1
goto :eof

:log_success
echo [SUCCESS] %~1
goto :eof

:log_warning
echo [WARNING] %~1
goto :eof

:log_error
echo [ERROR] %~1
goto :eof

:end
endlocal
exit /b 0