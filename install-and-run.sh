#!/bin/bash
# YTDownloader - Setup and Installation Script for Linux/macOS
# This script handles everything: checking, installing, and launching

set -e

# Color definitions
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "============================================================"
echo "                   YTDownloader Setup"
echo "            Advanced YouTube Video Downloader"
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
APP_DIR=$(dirname "$(realpath "$0")")
VENV_PATH="/tmp/ytdownloader_venv"
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
        echo "Creating new virtual environment..."
        python3 -m venv "$VENV_PATH"
        echo -e "${GREEN}[OK] Virtual environment created${NC}"
    else
        echo "Using existing virtual environment"
    fi
else
    echo "Creating new virtual environment..."
    python3 -m venv "$VENV_PATH"
    echo -e "${GREEN}[OK] Virtual environment created${NC}"
fi
PYTHON_EXE="$VENV_PATH/bin/python"
echo ""

# Step 4: Install dependencies
echo "[Step 4] Installing Python dependencies..."
echo "This may take a few minutes..."
echo "Upgrading pip..."
"$PYTHON_EXE" -m pip install --upgrade pip
echo "Installing dependencies from requirements.txt..."
"$PYTHON_EXE" -m pip install -r "$APP_DIR/requirements.txt"
echo -e "${GREEN}[OK] All dependencies installed${NC}"
echo ""

# Step 5: Launch the application
echo "[Step 5] Launching YTDownloader..."
echo "Starting the application GUI..."
echo ""

if [ ! -f "$APP_DIR/main.py" ]; then
    echo -e "${RED}ERROR: main.py not found${NC}"
    exit 1
fi

"$PYTHON_EXE" "$APP_DIR/main.py" &

echo -e "${GREEN}"
echo "============================================================"
echo "          Setup Complete! YTDownloader is Ready"
echo "============================================================"
echo -e "${NC}"
echo "Next time you can launch YTDownloader by:"
echo "  1. Running this script again"
echo "  2. Command: \"$PYTHON_EXE\" \"$APP_DIR/main.py\""
echo ""
echo "Configuration and logs are saved to:"
echo "  Settings: ~/.ytdownloader/config.json"
echo "  Logs: $APP_DIR/ytdownloader.log"
echo ""
echo "For help and documentation, visit:"
echo "  https://github.com/AmirrezaFarnamTaheri/YTDownloader"
echo ""
