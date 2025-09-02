#!/bin/bash

echo "🚀 Starting vLLM Gateway in Production Mode..."

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "📝 Creating .env file from template..."
    
    if [ -f "env_example" ]; then
        cp env_example .env
        echo "✅ Created .env file from env_example"
        echo "🔧 Please edit .env file with your actual values before continuing"
        echo "   - Set VLLM_API_KEY to your actual vLLM API key"
        echo "   - Update VLLM_URL if needed"
        echo ""
        echo "Press Enter to continue after editing .env file..."
        read
    else
        echo "❌ env_example file not found. Please create .env file manually with:"
        echo "   VLLM_URL=http://localhost:8000/v1"
        echo "   VLLM_API_KEY=your_actual_key_here"
        echo "   DATABASE_PATH=./gateway.db"
        echo "   GATEWAY_PORT=8001"
        exit 1
    fi
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Start the gateway
echo "🚀 Starting gateway..."
python3 gateway.py
