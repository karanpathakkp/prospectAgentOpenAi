#!/bin/bash

# Prospect Research API Startup Script

echo "🚀 Starting Prospect Research API..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

# Check if requirements.txt exists
if [ ! -f "requirements.txt" ]; then
    echo "❌ requirements.txt not found. Please ensure you're in the correct directory."
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating template..."
    cat > .env << EOF
# API Keys (replace with your actual keys)
TAVILY_API_KEY=your_tavily_api_key_here
FIRECRAWL_API_KEY=your_firecrawl_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Configuration
TARGET_COMPANY=OpenAI
ENVIRONMENT=development
desired_profile=10
EOF
    echo "📝 Created .env template. Please edit it with your API keys before running again."
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt

# Check if installation was successful
if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies. Please check your Python environment."
    exit 1
fi

# Start the API
echo "🌐 Starting API server on http://localhost:8000"
echo "📚 API Documentation will be available at:"
echo "   - Interactive docs: http://localhost:8000/docs"
echo "   - ReDoc: http://localhost:8000/redoc"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python3 api.py 