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
