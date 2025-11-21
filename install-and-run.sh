#!/bin/bash
# Lumina - Setup and Installation Script for Linux/macOS
# This script handles everything: checking, installing, and launching

set -euo pipefail

# Setup logging
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/lumina_installer.log"
exec &> >(tee -a "$LOG_FILE")

# Color definitions
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

create_virtualenv() {
    echo "Creating new virtual environment..."
    if ! python3 -m venv "$VENV_PATH"; then
        echo -e "${RED}ERROR: Failed to create virtual environment.${NC}"
        echo "Please ensure the Python venv/ensurepip modules are installed (e.g., 'sudo apt install python3-venv')."
        exit 1
    fi
    echo -e "${GREEN}[OK] Virtual environment created${NC}"
}

ensure_pip_in_venv() {
    if ! "$PYTHON_EXE" -m pip --version >/dev/null 2>&1; then
        echo -e "${YELLOW}pip is missing from the virtual environment. Recreating it automatically...${NC}"
        rm -rf "$VENV_PATH"
        create_virtualenv
        PYTHON_EXE="$VENV_PATH/bin/python"
        if ! "$PYTHON_EXE" -m pip --version >/dev/null 2>&1; then
            echo -e "${RED}ERROR: pip is still unavailable. Install python3-venv (or the platform equivalent) and rerun the installer.${NC}"
            exit 1
        fi
    fi
}

echo -e "${CYAN}"
echo "============================================================"
echo "                   Lumina Setup"
echo "            Modern Media Downloader"
echo "                 Linux/macOS Installation"
echo "============================================================"
echo -e "${NC}"

# Step 1: Check if Python is installed
echo "[Step 1] Checking Python installation..."
if ! command -v python3 &> /dev/null
then
    echo -e "${RED}ERROR: Python 3 is not installed or not in PATH${NC}"
    echo "Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo -e "${GREEN}[OK] $PYTHON_VERSION${NC}"
echo ""

# Step 2: Get application directory
echo "[Step 2] Setting up application directory..."
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$APP_DIR/venv"
PYTHON_EXE="python3"

echo "Application directory: $APP_DIR"
echo ""

# Step 3: Create virtual environment
echo "[Step 3] Setting up virtual environment..."
if [ -d "$VENV_PATH" ]; then
    echo -e "${YELLOW}Virtual environment already exists.${NC}"
    read -p "Use existing virtual environment? (Y/n): " USE_EXISTING
    if [[ "$USE_EXISTING" == "n" || "$USE_EXISTING" == "N" ]]; then
        echo "Removing existing virtual environment..."
        rm -rf "$VENV_PATH"
        create_virtualenv
    else
        echo "Using existing virtual environment"
    fi
else
    create_virtualenv
fi
PYTHON_EXE="$VENV_PATH/bin/python"
ensure_pip_in_venv
echo ""

# Step 4: Install dependencies
echo "[Step 4] Installing Python dependencies..."
echo "This may take a few minutes..."

# Check for proxy.txt file (for consistency with other scripts)
PROXY_URL=""
if [ -f "$APP_DIR/proxy.txt" ]; then
    PROXY_URL=$(head -n 1 "$APP_DIR/proxy.txt" | tr -d '\r\n')
    echo -e "${CYAN}Found proxy.txt, using proxy: $PROXY_URL${NC}"
fi

echo "Upgrading pip..."
if [ -n "$PROXY_URL" ]; then
    "$PYTHON_EXE" -m pip install --upgrade pip --proxy "$PROXY_URL" || {
        echo -e "${YELLOW}WARNING: Failed to upgrade pip. Continuing anyway...${NC}"
    }
else
    "$PYTHON_EXE" -m pip install --upgrade pip || {
        echo -e "${YELLOW}WARNING: Failed to upgrade pip. Continuing anyway...${NC}"
    }
fi

echo "Installing dependencies from requirements.txt..."
if [ ! -f "$APP_DIR/requirements.txt" ]; then
    echo -e "${RED}ERROR: requirements.txt not found${NC}"
    exit 1
fi

if [ -n "$PROXY_URL" ]; then
    "$PYTHON_EXE" -m pip install -r "$APP_DIR/requirements.txt" --proxy "$PROXY_URL" || {
        echo -e "${RED}ERROR: Failed to install dependencies. Please check the output above for errors.${NC}"
        exit 1
    }
else
    "$PYTHON_EXE" -m pip install -r "$APP_DIR/requirements.txt" || {
        echo -e "${RED}ERROR: Failed to install dependencies. Please check the output above for errors.${NC}"
        exit 1
    }
fi
echo -e "${GREEN}[OK] All dependencies installed${NC}"
echo ""

# Step 5: Launch the application
echo "[Step 5] Launching Lumina..."
echo "Starting the application GUI..."
echo ""

if [ ! -f "$APP_DIR/main.py" ]; then
    echo -e "${RED}ERROR: main.py not found${NC}"
    exit 1
fi

"$PYTHON_EXE" "$APP_DIR/main.py" > /dev/null 2>&1 &

echo -e "${GREEN}"
echo "============================================================"
echo "          Setup Complete! Lumina is Ready"
echo "============================================================"
echo -e "${NC}"
echo "Next time you can launch Lumina by:"
echo "  1. Running this script again"
echo "  2. Command: \"$PYTHON_EXE\" \"$APP_DIR/main.py\""
echo ""
echo "Configuration and logs are saved to:"
echo "  Settings: ~/.lumina/config.json"
echo "  Logs: $APP_DIR/lumina.log"
echo "  Installer log: $LOG_FILE"
echo ""
