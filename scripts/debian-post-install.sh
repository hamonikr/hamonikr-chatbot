#!/bin/bash

# Hamonikr Chatbot Debian Post-Install Script
# 데비안 패키지 설치 후 자동으로 실행되어 필요한 설정을 완료합니다

set -e

# Configuration
VENV_NAME="hamonikr-chatbot-venv"
VENV_PATH="$HOME/.local/share/$VENV_NAME"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

print_header() {
    echo -e "${BLUE}[HEADER]${NC} $1"
}

# Check if running as root
check_root() {
    if [ "$EUID" -eq 0 ]; then
        print_error "이 스크립트는 root 권한으로 실행하면 안 됩니다."
        print_error "일반 사용자로 실행하세요."
        exit 1
    fi
}

# Check if PyGObject is available
check_pygobject() {
    print_status "PyGObject 설치를 확인합니다..."
    
    if python3 -c "import gi; from gi.repository import Gtk; print('PyGObject 사용 가능')" 2>/dev/null; then
        print_status "PyGObject가 정상적으로 설치되어 있습니다 ✓"
        return 0
    else
        print_warning "PyGObject가 설치되지 않았습니다 ✗"
        return 1
    fi
}

# Install PyGObject if missing
install_pygobject() {
    print_status "PyGObject를 설치합니다..."
    
    # Check if apt is available
    if command -v apt &> /dev/null; then
        print_status "apt를 사용하여 PyGObject를 설치합니다..."
        
        sudo apt update
        sudo apt install -y \
            python3-gi \
            python3-gi-cairo \
            gir1.2-gtk-4.0 \
            gir1.2-adw-1 \
            gir1.2-webkit2-4.0
        
        if [ $? -eq 0 ]; then
            print_status "PyGObject 설치 성공 ✓"
            return 0
        else
            print_error "PyGObject 설치 실패 ✗"
            return 1
        fi
    else
        print_error "apt 패키지 매니저를 찾을 수 없습니다."
        print_error "수동으로 PyGObject를 설치해야 합니다."
        return 1
    fi
}

# Create or fix virtual environment
setup_virtual_environment() {
    print_status "가상환경을 설정합니다..."
    
    # Check if virtual environment exists
    if [ -d "$VENV_PATH" ]; then
        print_status "기존 가상환경이 발견되었습니다: $VENV_PATH"
        
        # Check if it's valid
        if [ -f "$VENV_PATH/bin/activate" ] && [ -f "$VENV_PATH/bin/python" ]; then
            print_status "가상환경이 유효합니다."
        else
            print_warning "가상환경이 손상되었습니다. 재생성이 필요합니다."
            remove_corrupted_venv
            create_new_venv
        fi
    else
        print_status "가상환경이 존재하지 않습니다. 새로 생성합니다."
        create_new_venv
    fi
}

# Remove corrupted virtual environment
remove_corrupted_venv() {
    print_status "손상된 가상환경을 제거합니다..."
    rm -rf "$VENV_PATH"
    print_status "가상환경 제거 완료"
}

# Create new virtual environment
create_new_venv() {
    print_status "새로운 가상환경을 생성합니다: $VENV_PATH"
    
    # Create virtual environment with system site packages
    python3 -m venv --system-site-packages "$VENV_PATH"
    
    if [ $? -eq 0 ]; then
        print_status "가상환경 생성 성공 ✓"
    else
        print_error "가상환경 생성 실패 ✗"
        exit 1
    fi
}

# Activate virtual environment and install packages
install_python_packages() {
    print_status "Python 패키지를 설치합니다..."
    
    # Activate virtual environment
    source "$VENV_PATH/bin/activate"
    
    # Verify activation
    if [ -n "$VIRTUAL_ENV" ]; then
        print_status "가상환경 활성화 성공: $VIRTUAL_ENV"
    else
        print_error "가상환경 활성화 실패"
        exit 1
    fi
    
    # Upgrade pip
    print_status "pip을 최신 버전으로 업그레이드합니다..."
    pip install --upgrade pip
    
    # Install requirements
    local requirements_file="$PROJECT_ROOT/requirements.txt"
    if [ -f "$requirements_file" ]; then
        print_status "requirements.txt에서 패키지를 설치합니다..."
        pip install -r "$requirements_file"
        
        if [ $? -eq 0 ]; then
            print_status "패키지 설치 성공 ✓"
        else
            print_error "패키지 설치 실패 ✗"
            exit 1
        fi
    else
        print_warning "requirements.txt 파일을 찾을 수 없습니다."
        print_status "기본 패키지를 설치합니다..."
        pip install openai requests tqdm pillow babel google-generativeai
    fi
    
    # Test installation
    test_installation
    
    # Deactivate
    deactivate
}

# Test installation
test_installation() {
    print_status "설치를 테스트합니다..."
    
    # Test PyGObject in virtual environment
    if python -c "import gi; from gi.repository import Gtk; print('✓ 가상환경에서 PyGObject 사용 가능')" 2>/dev/null; then
        print_status "가상환경에서 PyGObject 정상 작동 ✓"
    else
        print_warning "가상환경에서 PyGObject 오류 ✗"
    fi
    
    # Test other packages
    if python -c "import openai; print(f'✓ OpenAI 버전: {openai.__version__}')" 2>/dev/null; then
        print_status "OpenAI 라이브러리 접근 가능 ✓"
    else
        print_error "OpenAI 라이브러리 접근 불가 ✗"
    fi
    
    if python -c "import google.generativeai; print('✓ Google Generative AI 사용 가능')" 2>/dev/null; then
        print_status "Google Generative AI 접근 가능 ✓"
    else
        print_error "Google Generative AI 접근 불가 ✗"
    fi
}

# Create activation script
create_activation_script() {
    local activation_script="$PROJECT_ROOT/activate-venv.sh"
    print_status "활성화 스크립트를 생성합니다: $activation_script"
    
    cat > "$activation_script" << 'EOF'
#!/bin/bash
# HamoniKR Chatbot Virtual Environment Activation Script

VENV_NAME="hamonikr-chatbot-venv"
VENV_PATH="$HOME/.local/share/$VENV_NAME"

if [ -d "$VENV_PATH" ] && [ -f "$VENV_PATH/bin/activate" ]; then
    source "$VENV_PATH/bin/activate"
    echo "✓ 가상환경이 활성화되었습니다."
    echo "  Python 경로: $(which python)"
    echo "  가상환경: $VIRTUAL_ENV"
    echo ""
    echo "가상환경을 비활성화하려면: deactivate"
    echo "GTK 및 기타 시스템 패키지에 접근할 수 있습니다."
else
    echo "✗ 가상환경을 찾을 수 없습니다."
    echo "  먼저 debian-post-install.sh를 실행하세요."
    exit 1
fi
EOF
    
    chmod +x "$activation_script"
    print_status "활성화 스크립트 생성 완료"
}

# Create desktop shortcut
create_desktop_shortcut() {
    print_status "데스크톱 바로가기를 생성합니다..."
    
    local desktop_file="$HOME/.local/share/applications/hamonikr-chatbot.desktop"
    
    cat > "$desktop_file" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Hamonikr Chatbot
Comment=AI 챗봇 애플리케이션
Exec=$VENV_PATH/bin/python $PROJECT_ROOT/src/main.py
Icon=$PROJECT_ROOT/data/icons/hicolor/scalable/apps/io.github.Bavarder.Bavarder.svg
Terminal=false
Categories=Utility;AI;Chat;
Keywords=chatbot;ai;gpt;openai;gemini;
EOF
    
    chmod +x "$desktop_file"
    print_status "데스크톱 바로가기 생성 완료: $desktop_file"
}

# Main function
main() {
    print_header "Hamonikr Chatbot Debian Post-Install 설정"
    print_header "=========================================="
    
    # Check if not running as root
    check_root
    
    # Check and install PyGObject if needed
    if ! check_pygobject; then
        print_warning "PyGObject가 설치되지 않았습니다. 설치를 진행합니다..."
        if ! install_pygobject; then
            print_error "PyGObject 설치에 실패했습니다."
            print_error "수동으로 설치하거나 시스템을 재부팅해보세요."
            exit 1
        fi
    fi
    
    # Setup virtual environment
    setup_virtual_environment
    
    # Install Python packages
    install_python_packages
    
    # Create scripts and shortcuts
    create_activation_script
    create_desktop_shortcut
    
    print_header "설정 완료!"
    print_status "가상환경 위치: $VENV_PATH"
    print_status "활성화 방법: source $VENV_PATH/bin/activate"
    print_status "또는: $PROJECT_ROOT/activate-venv.sh"
    print_status ""
    print_status "데스크톱 바로가기가 생성되었습니다."
    print_status "이제 Hamonikr Chatbot을 실행할 수 있습니다!"
}

# Run main function
main "$@"
