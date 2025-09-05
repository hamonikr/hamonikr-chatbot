# HamoniKR Chatbot Installation Guide

## System Requirements

### Required System Packages

Before installing HamoniKR Chatbot, ensure you have the following GTK dependencies installed:

```bash
# For Ubuntu/Debian/HamoniKR:
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1

# For Fedora/RHEL:
sudo dnf install python3-gobject gtk4-devel libadwaita-devel

# For Arch Linux:
sudo pacman -S python-gobject gtk4 libadwaita
```

### Python Dependencies

The application requires Python 3.10+ and will automatically manage the following dependencies:
- OpenAI API library (1.12.0 <= version < 2.0.0)
- Additional packages: requests, tqdm, pillow, babel, packaging, markitdown, etc.

## Installation Methods

### Method 1: Install from Debian Package (Recommended for Ubuntu/HamoniKR)

1. Build the Debian package:
```bash
dpkg-buildpackage -b -uc -us
```

2. Install the package:
```bash
sudo dpkg -i ../hamonikr-chatbot_*.deb
sudo apt-get install -f  # Fix any dependency issues
```

### Method 2: Build from Source

1. Install build dependencies:
```bash
sudo apt install meson ninja-build blueprint-compiler python3-lxml
```

2. Configure and build:
```bash
meson setup build --prefix=/usr
ninja -C build
```

3. Install:
```bash
sudo ninja -C build install
```

## Runtime Environment

### Automatic Dependency Management

The launcher script automatically handles Python dependencies:

1. **System Python First**: If compatible versions of packages are available system-wide, they will be used
2. **Virtual Environment Fallback**: If system packages are incompatible or missing, a virtual environment is created at `~/.local/share/hamonikr-chatbot-venv/`
3. **GTK Binding Preservation**: GTK bindings (PyGObject) always use system packages to avoid compatibility issues

### Manual Dependency Installation (Optional)

If you prefer to manage dependencies manually:

```bash
# For user-space installation (Ubuntu 24.04+):
pip3 install --user --break-system-packages "openai>=1.12.0,<2.0.0"
pip3 install --user --break-system-packages requests tqdm pillow babel packaging

# For older systems without PEP 668 restrictions:
pip3 install --user "openai>=1.12.0,<2.0.0"
pip3 install --user requests tqdm pillow babel packaging
```

## New Features

### System Prompt Definition
- Access through Preferences → System Prompts
- Define custom system prompts for all AI conversations
- Prompts are persisted across sessions

### MCP Server Management
- Access through Preferences → MCP Servers
- Add Model Context Protocol servers for extended AI capabilities
- Support for stdio, TCP, and Unix socket connections
- Enable/disable servers individually

## Troubleshooting

### "No module named 'gi'" Error
Ensure GTK Python bindings are installed:
```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1
```

### OpenAI Module Issues
The launcher will automatically create a virtual environment if needed. To reset:
```bash
rm -rf ~/.local/share/hamonikr-chatbot-venv/
```

### Permission Denied Errors
Ensure the launcher script is executable:
```bash
chmod +x /usr/bin/hamonikr-chatbot
```

## Configuration Files

- Settings: `~/.config/glib-2.0/settings/org.hamonikr.Chatbot`
- Virtual Environment: `~/.local/share/hamonikr-chatbot-venv/`
- Application Data: `/usr/share/hamonikr-chatbot/`

## Development

For development, you can run directly from the build directory:
```bash
./build/src/hamonikr-chatbot --debug
```

Debug mode provides additional output for troubleshooting.