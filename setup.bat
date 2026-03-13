@echo off
REM =============================================================
REM Explorion Project Setup Script (Windows)
REM =============================================================
REM This script sets up the full-stack Explorion application
REM Requirements: Node.js, npm, Python 3.8+, pip, Docker, Docker Compose
REM =============================================================

setlocal enabledelayedexpansion

REM Colors for output (Windows CMD)
REM Note: Windows CMD doesn't support ANSI colors well, using plain text
set "RED=[ERROR]"
set "GREEN=[SUCCESS]"
set "YELLOW=[WARNING]"
set "BLUE=[INFO]"

REM Logging functions
:log_info
echo %BLUE% %~1
goto :eof

:log_success
echo %GREEN% %~1
goto :eof

:log_warning
echo %YELLOW% %~1
goto :eof

:log_error
echo %RED% %~1
goto :eof

REM Error handler
:error_exit
call :log_error "%~1"
echo [ERROR] Setup failed. Please check the errors above and try again.
pause
exit /b 1

REM Check if command exists
:check_command
where "%~1" >nul 2>nul
if %errorlevel% neq 0 (
    call :error_exit "%~1 is not installed. Please install %~1 and try again."
)
goto :eof

REM Check Node.js version
:check_node_version
for /f "tokens=*" %%i in ('node -v') do set NODE_VERSION=%%i
set NODE_VERSION=%NODE_VERSION:v=%
for /f "tokens=1 delims=." %%a in ("%NODE_VERSION%") do set NODE_MAJOR=%%a
if %NODE_MAJOR% lss 18 (
    call :error_exit "Node.js version 18+ is required. Current version: %NODE_VERSION%"
)
goto :eof

REM Check Python version
:check_python_version
for /f "tokens=*" %%i in ('python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}') 2^>nul') do set PYTHON_VERSION=%%i
if "%PYTHON_VERSION%"=="" (
    REM Try python3
    for /f "tokens=*" %%i in ('python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}') 2^>nul') do set PYTHON_VERSION=%%i
)
if "%PYTHON_VERSION%"=="" (
    call :error_exit "Python is not accessible. Please ensure Python 3.8+ is installed."
)
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set PYTHON_MAJOR=%%a
    set PYTHON_MINOR=%%b
)
if %PYTHON_MAJOR% lss 3 (
    call :error_exit "Python 3.8+ is required. Current version: %PYTHON_VERSION%"
)
if %PYTHON_MAJOR%==3 if %PYTHON_MINOR% lss 8 (
    call :error_exit "Python 3.8+ is required. Current version: %PYTHON_VERSION%"
)
goto :eof

REM Main setup function
:main
echo ========================================
echo 🚀 Setting up Explorion Project
echo ========================================

REM Check prerequisites
call :log_info "Checking prerequisites..."

call :check_command "node"
call :check_command "npm"
call :check_command "python"
call :check_command "pip"
call :check_command "docker"
call :check_command "docker-compose"

call :check_node_version
call :check_python_version

call :log_success "All prerequisites are installed!"

REM Setup backend
call :log_info "Setting up backend..."
cd backend
if %errorlevel% neq 0 (
    call :error_exit "Backend directory not found"
)

REM Check if .env exists
if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        call :log_success "Created .env from .env.example"
        call :log_warning "Please edit backend\.env with your actual API keys"
    ) else (
        call :error_exit ".env.example not found in backend directory"
    )
) else (
    call :log_info ".env already exists"
)

REM Install Python dependencies
call :log_info "Installing Python dependencies..."
pip install -r requirements.txt
if %errorlevel% neq 0 (
    call :error_exit "Failed to install Python dependencies"
)

call :log_success "Backend setup complete!"

REM Setup frontend
cd ..\frontend
if %errorlevel% neq 0 (
    call :error_exit "Frontend directory not found"
)
call :log_info "Setting up frontend..."

REM Install Node dependencies
call :log_info "Installing Node.js dependencies..."
npm install
if %errorlevel% neq 0 (
    call :error_exit "Failed to install Node.js dependencies"
)

call :log_success "Frontend setup complete!"

REM Return to root
cd ..
if %errorlevel% neq 0 (
    call :error_exit "Could not return to project root"
)

REM Final instructions
echo.
echo ========================================
call :log_success "🎉 Setup complete!"
echo.
echo Next steps:
echo 1. Edit backend\.env with your API keys
echo 2. Start the backend: cd backend ^& python main.py
echo 3. Start the frontend: cd frontend ^& npm run dev
echo 4. Or use Docker: docker-compose up
echo.
call :log_info "Happy coding! 🚀"
goto :eof

REM Run main function
call :main %*