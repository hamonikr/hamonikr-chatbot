#!/bin/bash

# HamoniKR Chatbot Launcher Script
# This script ensures the virtual environment is set up and runs the chatbot

set -e

# Configuration
VENV_NAME="hamonikr-chatbot-venv"
VENV_PATH="$HOME/.local/share/$VENV_NAME"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SETUP_SCRIPT="$SCRIPT_DIR/setup-venv.sh"

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

# Check if virtual environment exists
check_venv() {
    if [ ! -d "$VENV_PATH" ]; then
        print_warning "Virtual environment not found. Setting up..."
        if [ -f "$SETUP_SCRIPT" ]; then
            bash "$SETUP_SCRIPT"
        else
            print_error "Setup script not found at $SETUP_SCRIPT"
            exit 1
        fi
    fi
}

# Activate virtual environment
activate_venv() {
    if [ -f "$VENV_PATH/bin/activate" ]; then
        source "$VENV_PATH/bin/activate"
        print_status "Virtual environment activated"
    else
        print_error "Virtual environment activation script not found"
        exit 1
    fi
}

# Check if required packages are installed
check_dependencies() {
    if ! python -c "import openai; print('OpenAI version:', openai.__version__)" 2>/dev/null; then
        print_warning "Dependencies not properly installed. Reinstalling..."
        if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
            pip install -r "$PROJECT_ROOT/requirements.txt"
        else
            pip install "openai>=1.12.0,<2.0.0" requests tqdm pillow babel
        fi
    fi
}

# Run the chatbot
run_chatbot() {
    print_status "Starting HamoniKR Chatbot..."
    
    # Change to project directory
    cd "$PROJECT_ROOT"
    
    # Set environment variables if needed
    export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"
    
    # Run the main application
    # This assumes the main script is in src/main.py or similar
    if [ -f "$PROJECT_ROOT/src/main.py" ]; then
        python "$PROJECT_ROOT/src/main.py" "$@"
    elif [ -f "$PROJECT_ROOT/main.py" ]; then
        python "$PROJECT_ROOT/main.py" "$@"
    else
        # Try to find the main entry point
        print_warning "Main script not found. Trying to run as module..."
        python -m hamonikr_chatbot "$@" 2>/dev/null || {
            print_error "Could not find main entry point"
            print_error "Please check the project structure"
            exit 1
        }
    fi
}

# Main function
main() {
    print_status "HamoniKR Chatbot Launcher"
    
    check_venv
    activate_venv
    check_dependencies
    run_chatbot "$@"
}

# Trap to deactivate virtual environment on exit
cleanup() {
    if command -v deactivate &> /dev/null; then
        deactivate 2>/dev/null || true
    fi
}
trap cleanup EXIT

# Run main function
main "$@"