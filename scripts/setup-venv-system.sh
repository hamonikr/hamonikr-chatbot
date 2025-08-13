#!/bin/bash

# HamoniKR Chatbot Virtual Environment Setup Script (with system site packages)
# This script creates a virtual environment that can access system packages like GTK

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

# Remove existing virtual environment
remove_existing_venv() {
    if [ -d "$VENV_PATH" ]; then
        print_status "Removing existing virtual environment..."
        rm -rf "$VENV_PATH"
    fi
}

# Create virtual environment with system site packages
create_venv_with_system() {
    print_status "Creating virtual environment with system site packages at $VENV_PATH"
    python3 -m venv --system-site-packages "$VENV_PATH"
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
        # Use --force-reinstall to ensure we get the versions we want
        pip install --force-reinstall -r "$REQUIREMENTS_FILE"
    else
        print_warning "Requirements file not found at $REQUIREMENTS_FILE"
        print_status "Installing basic dependencies..."
        pip install --force-reinstall "openai>=1.12.0,<2.0.0" requests tqdm pillow babel
    fi
}

# Test system packages
test_system_packages() {
    print_status "Testing system package access..."
    
    if python -c "import gi; from gi.repository import Gtk; print('GTK available')" 2>/dev/null; then
        print_status "GTK bindings accessible ✓"
    else
        print_error "GTK bindings not accessible ✗"
    fi
    
    if python -c "import openai; print(f'OpenAI version: {openai.__version__}')" 2>/dev/null; then
        print_status "OpenAI library accessible ✓"
    else
        print_error "OpenAI library not accessible ✗"
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
    echo "GTK and other system packages are accessible."
else
    echo "Virtual environment not found. Run setup-venv-system.sh first."
    exit 1
fi
EOF
    
    chmod +x "$activation_script"
}

# Main setup function
main() {
    print_status "Setting up HamoniKR Chatbot virtual environment with system packages..."
    
    remove_existing_venv
    create_venv_with_system
    activate_venv
    upgrade_pip
    install_requirements
    test_system_packages
    create_activation_script
    
    print_status "Setup complete!"
    print_status "Virtual environment created at: $VENV_PATH"
    print_status "System packages (GTK, etc.) are accessible"
    print_status "To activate manually: source $VENV_PATH/bin/activate"
    print_status "Or use: $PROJECT_ROOT/activate-venv.sh"
}

# Run main function
main "$@"