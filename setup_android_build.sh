#!/bin/bash
# Setup script for Android build environment using Buildozer

set -e

echo "====== Android Build Environment Setup ======"
echo "This script will set up the Android SDK and build tools for Buildozer"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"
for cmd in git java javac keytool python3 pip cython; do
    if ! command -v $cmd &> /dev/null; then
        echo -e "${RED}Error: $cmd is not installed${NC}"
        exit 1
    fi
done
echo -e "${GREEN}All prerequisites found${NC}"
echo ""

# Install/upgrade buildozer
echo -e "${YELLOW}Installing buildozer and cython...${NC}"
pip install --upgrade buildozer cython==0.29.33
echo -e "${GREEN}Buildozer installed${NC}"
echo ""

# Create Android SDK directory structure
echo -e "${YELLOW}Creating Android SDK directory structure...${NC}"
mkdir -p ~/.buildozer/android/platform/android-sdk/cmdline-tools
mkdir -p ~/.android
touch ~/.android/repositories.cfg
echo -e "${GREEN}Directories created${NC}"
echo ""

# Download and setup Android Command Line Tools
echo -e "${YELLOW}Downloading Android Command Line Tools...${NC}"
echo "This may take a few minutes..."
cd ~/.buildozer/android/platform/android-sdk/cmdline-tools

if [ -f "commandlinetools-linux-11076708_latest.zip" ]; then
    echo "Command line tools already downloaded"
else
    # Try multiple download sources
    if ! wget -q -O commandlinetools-linux-11076708_latest.zip https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip; then
        echo -e "${YELLOW}Primary download failed, trying alternative...${NC}"
        if ! curl -L -o commandlinetools-linux-11076708_latest.zip https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip; then
            echo -e "${RED}Failed to download Android command line tools${NC}"
            echo "Please download manually from: https://developer.android.com/studio/command-line"
            exit 1
        fi
    fi
fi

echo -e "${YELLOW}Extracting Android command line tools...${NC}"
unzip -q commandlinetools-linux-11076708_latest.zip
if [ -d "cmdline-tools" ]; then
    rm -rf latest
    mv cmdline-tools latest
fi
rm -f commandlinetools-linux-11076708_latest.zip
echo -e "${GREEN}Android command line tools installed${NC}"
echo ""

# Accept Android SDK licenses
echo -e "${YELLOW}Accepting Android SDK licenses...${NC}"
yes | ~/.buildozer/android/platform/android-sdk/cmdline-tools/latest/bin/sdkmanager --licenses || true
echo -e "${GREEN}Licenses accepted${NC}"
echo ""

# Install required SDK components
echo -e "${YELLOW}Installing required SDK components...${NC}"
echo "Installing: platform-tools, platforms;android-33, build-tools;33.0.0"
~/.buildozer/android/platform/android-sdk/cmdline-tools/latest/bin/sdkmanager \
    "platform-tools" \
    "platforms;android-33" \
    "build-tools;33.0.0"
echo -e "${GREEN}SDK components installed${NC}"
echo ""

# Verify setup
echo -e "${YELLOW}Verifying setup...${NC}"
if [ -f "~/.buildozer/android/platform/android-sdk/cmdline-tools/latest/bin/sdkmanager" ]; then
    echo -e "${GREEN}sdkmanager found at correct location${NC}"
else
    echo -e "${YELLOW}Warning: Could not verify sdkmanager location${NC}"
fi
echo ""

echo -e "${GREEN}====== Setup Complete ======${NC}"
echo "You can now run: cd mobile && buildozer android debug"
echo ""
