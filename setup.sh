#!/bin/bash

# =============================================================
# Explorion Project Setup Script
# =============================================================
# This script sets up the full-stack Explorion application
# Requirements: Node.js, npm, Python 3.8+, pip, Docker, Docker Compose
# =============================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Error handler
error_exit() {
    log_error "$1"
    echo -e "${RED}Setup failed. Please check the errors above and try again.${NC}"
    exit 1
}

# Check if command exists
check_command() {
    if ! command -v "$1" &> /dev/null; then
        error_exit "$1 is not installed. Please install $1 and try again."
    fi
}

# Check Node.js version
check_node_version() {
    local version=$(node -v | sed 's/v//')
    local major=$(echo $version | cut -d. -f1)
    if [ "$major" -lt 18 ]; then
        error_exit "Node.js version 18+ is required. Current version: $version"
    fi
}

# Check Python version
check_python_version() {
    # Try python3 first, then python
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
        PIP_CMD="pip3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
        PIP_CMD="pip"
    else
        error_exit "Python is not installed. Please install Python 3.8+ and try again."
    fi

    local version=$($PYTHON_CMD -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    local major=$(echo $version | cut -d. -f1)
    local minor=$(echo $version | cut -d. -f2)
    if [ "$major" -lt 3 ] || ([ "$major" -eq 3 ] && [ "$minor" -lt 8 ]); then
        error_exit "Python 3.8+ is required. Current version: $version"
    fi
}

# Main setup function
main() {
    echo "========================================"
    echo "🚀 Setting up Explorion Project"
    echo "========================================"

    # Check prerequisites
    log_info "Checking prerequisites..."

    check_command "node"
    check_command "npm"
    check_command "python3"
    check_command "pip3"
    check_command "docker"
    check_command "docker-compose"

    check_node_version
    check_python_version

    log_success "All prerequisites are installed!"

    # Setup backend
    log_info "Setting up backend..."
    cd backend || error_exit "Backend directory not found"

    # Check if .env exists
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            log_success "Created .env from .env.example"
            log_warning "Please edit backend/.env with your actual API keys"
        else
            error_exit ".env.example not found in backend directory"
        fi
    else
        log_info ".env already exists"
    fi

    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        log_info "Creating Python virtual environment..."
        $PYTHON_CMD -m venv venv || error_exit "Failed to create virtual environment"
        log_success "Virtual environment created"
    else
        log_info "Virtual environment already exists"
    fi

    # Activate virtual environment
    log_info "Activating virtual environment..."
    source venv/bin/activate || error_exit "Failed to activate virtual environment"

    # Upgrade pip
    log_info "Upgrading pip..."
    pip install --upgrade pip || log_warning "Failed to upgrade pip, continuing..."

    # Install Python dependencies
    log_info "Installing Python dependencies..."
    pip install -r requirements.txt || error_exit "Failed to install Python dependencies"

    log_success "Backend setup complete!"

    # Setup frontend
    cd ../frontend || error_exit "Frontend directory not found"
    log_info "Setting up frontend..."

    # Install Node dependencies
    log_info "Installing Node.js dependencies..."
    npm install || error_exit "Failed to install Node.js dependencies"

    log_success "Frontend setup complete!"

    # Return to root
    cd .. || error_exit "Could not return to project root"

    # Final instructions
    echo ""
    echo "========================================"
    log_success "🎉 Setup complete!"
    echo ""
    echo "Next steps:"
    echo "1. Edit backend/.env with your API keys"
    echo "2. Activate virtual environment: cd backend && source venv/bin/activate"
    echo "3. Start the backend: python main.py"
    echo "4. Start the frontend: cd ../frontend && npm run dev"
    echo "5. Or use Docker: cd .. && docker-compose up"
    echo ""
    log_info "Happy coding! 🚀"
}

# Run main function
main "$@"