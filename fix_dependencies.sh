#!/bin/bash

# Fix Dependencies Script for Prospect Research API

echo "🔧 Fixing dependency issues..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

echo "📦 Uninstalling conflicting packages..."

# Uninstall potentially conflicting packages
pip3 uninstall -y pydantic pydantic-core typing-extensions

echo "📦 Installing correct package versions..."

# Install the correct versions
pip3 install pydantic==1.10.13
pip3 install -r requirements.txt

echo "✅ Dependencies fixed!"
echo ""
echo "🚀 You can now run the API with:"
echo "   python api.py"
echo ""
echo "   Or use the startup script:"
echo "   ./start_api.sh" 