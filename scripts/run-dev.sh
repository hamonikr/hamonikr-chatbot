#!/bin/bash

# HamoniKR Chatbot Development Runner
# This script runs the chatbot from source code using the virtual environment

set -e

# Configuration
VENV_NAME="hamonikr-chatbot-venv"
VENV_PATH="$HOME/.local/share/$VENV_NAME"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SRC_DIR="$PROJECT_ROOT/src"

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
        print_error "Virtual environment not found. Run './scripts/setup-venv.sh' first"
        exit 1
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
    print_status "Checking dependencies..."
    if ! python -c "import openai; print('OpenAI version:', openai.__version__)" 2>/dev/null; then
        print_error "OpenAI package not found in virtual environment"
        exit 1
    fi
    
    if ! python -c "import gi; from gi.repository import Gtk; print('GTK available')" 2>/dev/null; then
        print_error "GTK bindings not available"
        exit 1
    fi
}

# Set up environment for development
setup_environment() {
    export PYTHONPATH="$SRC_DIR:$PYTHONPATH"
    export VERSION="1.1.0-dev"
    export PKGDATA_DIR="$SRC_DIR"
    export LOCALE_DIR="/usr/share/locale"
    
    print_status "Environment set up for development"
    print_status "PYTHONPATH: $PYTHONPATH"
    print_status "Version: $VERSION"
}

# Build gresource if needed
build_resources() {
    local gresource_xml="$SRC_DIR/bavarder.gresource.xml"
    local gresource_file="$SRC_DIR/hamonikr-chatbot.gresource"
    
    if [ -f "$gresource_xml" ]; then
        print_status "Building GResource file..."
        cd "$SRC_DIR"
        if command -v glib-compile-resources &> /dev/null; then
            glib-compile-resources --target="$gresource_file" "$gresource_xml" 2>/dev/null || {
                print_warning "Could not build GResource file"
            }
        else
            print_warning "glib-compile-resources not found, skipping resource compilation"
        fi
        cd "$PROJECT_ROOT"
    fi
}

# Run the chatbot
run_chatbot() {
    print_status "Starting HamoniKR Chatbot from source..."
    
    # Change to project directory
    cd "$PROJECT_ROOT"
    
    # Try different entry points
    if [ -f "$SRC_DIR/main.py" ]; then
        print_status "Running main.py..."
        python "$SRC_DIR/main.py" "$@"
    elif [ -f "$SRC_DIR/bavarder.in" ]; then
        print_status "Creating temporary launcher from bavarder.in..."
        
        # Create a temporary main script
        local temp_main="/tmp/hamonikr-chatbot-main.py"
        cat > "$temp_main" << EOF
#!/usr/bin/env python3

import os
import sys
import signal
import locale
import gettext

VERSION = '$VERSION'
pkgdatadir = '$PKGDATA_DIR'
localedir = '$LOCALE_DIR'

sys.path.insert(1, pkgdatadir)
signal.signal(signal.SIGINT, signal.SIG_DFL)
locale.bindtextdomain('hamonikr-chatbot', localedir)
locale.textdomain('hamonikr-chatbot')
gettext.install('hamonikr-chatbot', localedir)

if __name__ == '__main__':
    import gi

    from gi.repository import Gio
    gresource_path = os.path.join(pkgdatadir, 'hamonikr-chatbot.gresource')
    if os.path.exists(gresource_path):
        resource = Gio.Resource.load(gresource_path)
        resource._register()
    else:
        print("Warning: GResource file not found at", gresource_path)

    from hamonikr_chatbot import main
    sys.exit(main.main(VERSION))
EOF
        
        python "$temp_main" "$@"
        rm -f "$temp_main"
    else
        print_error "Could not find main entry point"
        exit 1
    fi
}

# Main function
main() {
    print_status "HamoniKR Chatbot Development Runner"
    
    check_venv
    activate_venv
    check_dependencies
    setup_environment
    build_resources
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