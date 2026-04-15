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

# 2. Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv_build
source venv_build/bin/activate

# 3. Install core dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install customtkinter selenium webdriver-manager pyyaml python-dotenv pyinstaller

# 4. Execute build engine
echo "🏗️  Launching build engine..."
python3 package.py

# 5. Cleanup
echo "🧹 Cleaning up virtual environment..."
deactivate
# rm -rf venv_build

echo "-------------------------------------------"
echo "✅ Build Process Finished."
echo "   Find your native binary in the 'dist' folder."
