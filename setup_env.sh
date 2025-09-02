#!/bin/bash

echo "🔧 vLLM Gateway Environment Setup"
echo "=================================="
echo ""

# Check if .env already exists
if [ -f ".env" ]; then
    echo "⚠️  .env file already exists!"
    echo "Current contents:"
    cat .env
    echo ""
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Setup cancelled."
        exit 0
    fi
fi

echo "📝 Creating .env file..."

# Get vLLM API key from user
read -p "Enter your vLLM API key (e.g., supersecretkey): " VLLM_API_KEY
if [ -z "$VLLM_API_KEY" ]; then
    VLLM_API_KEY="supersecretkey"
    echo "Using default key: $VLLM_API_KEY"
fi

# Get vLLM URL from user
read -p "Enter vLLM backend URL [default: http://localhost:8000/v1]: " VLLM_URL
if [ -z "$VLLM_URL" ]; then
    VLLM_URL="http://localhost:8000/v1"
fi

# Get database path from user
read -p "Enter database path [default: ./gateway.db]: " DATABASE_PATH
if [ -z "$DATABASE_PATH" ]; then
    DATABASE_PATH="./gateway.db"
fi

# Get gateway port from user
read -p "Enter gateway port [default: 8001]: " GATEWAY_PORT
if [ -z "$GATEWAY_PORT" ]; then
    GATEWAY_PORT="8001"
fi

# Create .env file
cat > .env << EOF
# vLLM Gateway Configuration
VLLM_URL=$VLLM_URL
VLLM_API_KEY=$VLLM_API_KEY
DATABASE_PATH=$DATABASE_PATH
GATEWAY_PORT=$GATEWAY_PORT

# Optional: Hugging Face token for vLLM
# HF_TOKEN=your_huggingface_token_here
EOF

echo ""
echo "✅ .env file created successfully!"
echo ""
echo "📋 Configuration:"
echo "   VLLM_URL: $VLLM_URL"
echo "   VLLM_API_KEY: $VLLM_API_KEY"
echo "   DATABASE_PATH: $DATABASE_PATH"
echo "   GATEWAY_PORT: $GATEWAY_PORT"
echo ""
echo "🚀 You can now start the gateway with:"
echo "   ./start_production.sh"
echo ""
echo "🔒 Remember to keep your .env file secure and never commit it to version control!"
