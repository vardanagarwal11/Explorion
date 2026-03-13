#!/bin/bash

# =============================================================
# Explorion Project Setup Script (Unix/macOS/Linux)
# =============================================================
# Requirements: Node.js 18+, npm, Python 3.8+, pip, Docker, Docker Compose
# =============================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

error_exit() {
    log_error "$1"
    echo -e "${RED}Setup failed. Please check the errors above and try again.${NC}"
    exit 1
}

# -------------------------------------------------------
# Detect Python: tries python3, python, python3.x variants
# Sets globals: PYTHON_CMD, PIP_CMD
# -------------------------------------------------------
detect_python() {
    local candidates=("python3" "python" "python3.12" "python3.11" "python3.10" "python3.9" "python3.8")
    PYTHON_CMD=""
    PIP_CMD=""

    for cmd in "${candidates[@]}"; do
        if command -v "$cmd" &>/dev/null; then
            local ver
            ver=$("$cmd" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null) || continue
            local major minor
            major=$(echo "$ver" | cut -d. -f1)
            minor=$(echo "$ver" | cut -d. -f2)
            if [ "$major" -ge 3 ] && [ "$minor" -ge 8 ]; then
                PYTHON_CMD="$cmd"
                break
            fi
        fi
    done

    if [ -z "$PYTHON_CMD" ]; then
        error_exit "Python 3.8+ not found. Tried: ${candidates[*]}. Please install Python 3.8+ and re-run."
    fi

    # Detect matching pip
    local pip_candidates=("pip3" "pip" "${PYTHON_CMD} -m pip")
    for pip in "${pip_candidates[@]}"; do
        if $pip --version &>/dev/null 2>&1; then
            PIP_CMD="$pip"
            break
        fi
    done

    # Fall back to module pip
    if [ -z "$PIP_CMD" ]; then
        if "$PYTHON_CMD" -m pip --version &>/dev/null 2>&1; then
            PIP_CMD="$PYTHON_CMD -m pip"
        else
            error_exit "pip not found. Please install pip for $PYTHON_CMD."
        fi
    fi

    log_success "Using Python: $PYTHON_CMD ($($PYTHON_CMD --version 2>&1))"
    log_success "Using pip:    $PIP_CMD ($($PIP_CMD --version 2>&1 | head -1))"
}

# -------------------------------------------------------
# Detect Node.js 18+
# -------------------------------------------------------
detect_node() {
    if ! command -v node &>/dev/null; then
        error_exit "Node.js is not installed. Please install Node.js 18+ from https://nodejs.org"
    fi
    local ver major
    ver=$(node -v | sed 's/v//')
    major=$(echo "$ver" | cut -d. -f1)
    if [ "$major" -lt 18 ]; then
        error_exit "Node.js 18+ required. Current: v$ver. Please upgrade."
    fi
    log_success "Using Node.js: v$ver"
}

# -------------------------------------------------------
# Detect npm
# -------------------------------------------------------
detect_npm() {
    if ! command -v npm &>/dev/null; then
        error_exit "npm is not installed. It usually comes with Node.js — please reinstall Node.js."
    fi
    log_success "Using npm: $(npm -v)"
}

# -------------------------------------------------------
# Detect Docker (optional — warn, don't fail)
# -------------------------------------------------------
detect_docker() {
    if ! command -v docker &>/dev/null; then
        log_warning "Docker not found. You can still run the app manually without Docker."
        DOCKER_AVAILABLE=false
    else
        log_success "Using Docker: $(docker --version)"
        DOCKER_AVAILABLE=true
    fi

    COMPOSE_AVAILABLE=false
    if command -v docker-compose &>/dev/null; then
        log_success "Using Docker Compose: $(docker-compose --version)"
        COMPOSE_AVAILABLE=true
    elif docker compose version &>/dev/null 2>&1; then
        log_success "Using Docker Compose (plugin): $(docker compose version)"
        COMPOSE_AVAILABLE=true
    else
        log_warning "Docker Compose not found. You can still run the app manually."
    fi
}

# -------------------------------------------------------
# Activate a virtual environment — handles venv & conda
# Sets global: VENV_ACTIVATE (the activate script path)
# -------------------------------------------------------
activate_venv() {
    local venv_dir="$1"

    # Prefer the standard activate script
    if [ -f "$venv_dir/bin/activate" ]; then
        # shellcheck disable=SC1090
        source "$venv_dir/bin/activate" || error_exit "Failed to activate venv at $venv_dir/bin/activate"
        log_success "Virtual environment activated"
        return 0
    fi

    # macOS sometimes places it differently
    if [ -f "$venv_dir/Scripts/activate" ]; then
        # shellcheck disable=SC1090
        source "$venv_dir/Scripts/activate" || error_exit "Failed to activate venv at $venv_dir/Scripts/activate"
        log_success "Virtual environment activated"
        return 0
    fi

    error_exit "Could not find activate script in $venv_dir. The venv may be corrupted — delete the 'venv' folder and re-run."
}

# -------------------------------------------------------
# Backend setup
# -------------------------------------------------------
setup_backend() {
    log_info "Setting up backend..."

    [ -d "backend" ] || error_exit "backend/ directory not found. Run this script from the project root."
    cd backend

    # .env
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            log_success "Created backend/.env from .env.example"
            log_warning "⚠️  Please edit backend/.env with your actual API keys before starting the app."
        else
            log_warning "No .env.example found — skipping .env creation. Create backend/.env manually."
        fi
    else
        log_info "backend/.env already exists — skipping."
    fi

    # Virtual environment: recreate if broken
    if [ -d "venv" ]; then
        # Quick sanity check: can the Python inside still run?
        if ! venv/bin/python -c "import sys" &>/dev/null 2>&1 && \
           ! venv/Scripts/python -c "import sys" &>/dev/null 2>&1; then
            log_warning "Existing venv appears broken — removing and recreating..."
            rm -rf venv
        else
            log_info "Existing virtual environment found."
        fi
    fi

    if [ ! -d "venv" ]; then
        log_info "Creating Python virtual environment..."
        "$PYTHON_CMD" -m venv venv || error_exit "Failed to create virtual environment. Try: $PYTHON_CMD -m pip install virtualenv"
        log_success "Virtual environment created."
    fi

    activate_venv "venv"

    # After activation, pip should resolve to the venv's pip
    log_info "Upgrading pip inside venv..."
    python -m pip install --upgrade pip || log_warning "pip upgrade failed — continuing."

    if [ ! -f "requirements.txt" ]; then
        log_warning "requirements.txt not found in backend/ — skipping dependency install."
    else
        log_info "Installing Python dependencies..."
        python -m pip install -r requirements.txt || error_exit "Failed to install Python dependencies. Check requirements.txt."
    fi

    log_success "Backend setup complete!"
    cd ..
}

# -------------------------------------------------------
# Frontend setup
# -------------------------------------------------------
setup_frontend() {
    log_info "Setting up frontend..."

    [ -d "frontend" ] || error_exit "frontend/ directory not found. Run this script from the project root."
    cd frontend

    log_info "Installing Node.js dependencies..."
    npm install || error_exit "Failed to install Node.js dependencies. Try deleting node_modules and re-running."

    log_success "Frontend setup complete!"
    cd ..
}

# -------------------------------------------------------
# Main
# -------------------------------------------------------
main() {
    echo "========================================"
    echo "🚀  Setting up Explorion Project"
    echo "========================================"
    echo ""

    # Must be run from project root
    if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
        error_exit "Run this script from the project root (where backend/ and frontend/ folders exist)."
    fi

    log_info "Checking prerequisites..."
    detect_node
    detect_npm
    detect_python
    detect_docker
    echo ""

    setup_backend
    echo ""
    setup_frontend
    echo ""

    echo "========================================"
    log_success "🎉  Setup complete!"
    echo ""
    echo "Next steps:"
    echo "  1. Edit backend/.env with your API keys (if not done already)"
    echo ""
    echo "  Manual start:"
    echo "    Terminal 1 (backend):"
    echo "      cd backend"
    echo "      source venv/bin/activate"
    echo "      python main.py"
    echo ""
    echo "    Terminal 2 (frontend):"
    echo "      cd frontend"
    echo "      npm run dev"
    echo ""
    if [ "$COMPOSE_AVAILABLE" = true ]; then
        echo "  Docker start:"
        if command -v docker-compose &>/dev/null; then
            echo "      docker-compose up --build"
        else
            echo "      docker compose up --build"
        fi
        echo ""
    fi
    log_info "Happy coding! 🚀"
    echo "========================================"
}

main "$@"