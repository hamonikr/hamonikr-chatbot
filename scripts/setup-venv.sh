#!/bin/bash

# HamoniKR Chatbot Virtual Environment Setup Script
# This script creates and manages a virtual environment for HamoniKR Chatbot

set -e

# Configuration
VENV_NAME="hamonikr-chatbot-venv"
VENV_PATH="$HOME/.local/share/$VENV_NAME"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REQUIREMENTS_FILE="$PROJECT_ROOT/requirements.txt"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python 3 is available
check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed or not in PATH"
        exit 1
    fi
    
    local python_version=$(python3 --version | cut -d' ' -f2)
    print_status "Using Python $python_version"
}

# Create virtual environment if it doesn't exist
create_venv() {
    if [ ! -d "$VENV_PATH" ]; then
        print_status "Creating virtual environment at $VENV_PATH"
        python3 -m venv "$VENV_PATH"
    else
        print_status "Virtual environment already exists at $VENV_PATH"
    fi
}

# Activate virtual environment
activate_venv() {
    source "$VENV_PATH/bin/activate"
    print_status "Virtual environment activated"
}

# Install or upgrade pip
upgrade_pip() {
    print_status "Upgrading pip..."
    pip install --upgrade pip
}

# Install requirements
install_requirements() {
    if [ -f "$REQUIREMENTS_FILE" ]; then
        print_status "Installing requirements from $REQUIREMENTS_FILE"
        pip install -r "$REQUIREMENTS_FILE"
    else
        print_warning "Requirements file not found at $REQUIREMENTS_FILE"
        print_status "Installing basic dependencies..."
        pip install "openai>=1.12.0,<2.0.0" requests tqdm pillow babel
    fi
}

# Check if system packages conflict
check_conflicts() {
    print_status "Checking for potential conflicts..."
    
    # Check if user has conflicting packages installed globally
    if pip list --user | grep -q "openai\|httpx\|anyio"; then
        print_warning "Found user-installed packages that might conflict:"
        pip list --user | grep -E "openai|httpx|anyio" || true
        print_warning "Consider removing these with: pip uninstall openai httpx anyio"
    fi
}

# Create activation script
create_activation_script() {
    local activation_script="$PROJECT_ROOT/activate-venv.sh"
    print_status "Creating activation script at $activation_script"
    
    cat > "$activation_script" << 'EOF'
#!/bin/bash
# HamoniKR Chatbot Virtual Environment Activation Script

VENV_NAME="hamonikr-chatbot-venv"
VENV_PATH="$HOME/.local/share/$VENV_NAME"

if [ -d "$VENV_PATH" ]; then
    source "$VENV_PATH/bin/activate"
    echo "Virtual environment activated. To deactivate, run: deactivate"
else
    echo "Virtual environment not found. Run setup-venv.sh first."
    exit 1
fi
EOF
    
    chmod +x "$activation_script"
}

# Main setup function
main() {
    print_status "Setting up HamoniKR Chatbot virtual environment..."
    
    check_python
    create_venv
    activate_venv
    upgrade_pip
    install_requirements
    check_conflicts
    create_activation_script
    
    print_status "Setup complete!"
    print_status "Virtual environment created at: $VENV_PATH"
    print_status "To activate manually: source $VENV_PATH/bin/activate"
    print_status "Or use: $PROJECT_ROOT/activate-venv.sh"
}

# Run main function
main "$@"