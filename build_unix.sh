#!/bin/bash

# --- Sovereign Architecture: Unix Build Engine ---
# This script prepares the environment and builds the standalone binary on macOS/Linux.

echo "🚀 Starting Universal Sovereign Build (Unix)"
echo "-------------------------------------------"

# 1. Ensure Python 3 is installed
if ! command -v python3 &> /dev/null
then
    echo "❌ Error: Python 3 could not be found. Please install it first."
    exit 1
fi

# 2. Setup Environment
echo "📦 Setting up build environment..."
python3 -m pip install --upgrade pip
python3 -m pip install customtkinter pillow pyinstaller selenium webdriver-manager pyyaml python-dotenv

# 3. Execute Unified Build Engine
echo "🏗️  Launching build engine..."
python3 build.py

echo "-------------------------------------------"
echo "✅ Build Process Finished."
echo "   Find your native binary in the 'dist' folder."
