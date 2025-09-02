# vLLM Gateway

A **production-ready, secure gateway** that protects your vLLM API key while providing controlled access to clients through their own API keys. Features a beautiful web interface for API key management and AI chat.

## 🚀 Quick Start

### 1. Start vLLM Backend

```bash
docker run -it --rm -p 8000:8000 \
  --env "HUGGING_FACE_HUB_TOKEN=<your_hf_token>" \
  vllm-cpu --model meta-llama/Llama-3.2-1B-Instruct \
  --dtype float16 --api-key supersecretkey
```

### 2. Start the Gateway

```bash
# Install dependencies
pip install -r requirements.txt

# Start the production gateway (runs on port 8001)
python gateway.py
```

### 3. Access the Web Interface

Open your browser and navigate to:
- **Home Page**: http://localhost:8001
- **Dashboard**: http://localhost:8001/dashboard
- **API Keys**: http://localhost:8001/api/keys
- **Chat Interface**: http://localhost:8001/chat

## ✨ Features

### 🔐 Security & Authentication
- **Protected vLLM Key**: Your `supersecretkey` is never exposed to clients
- **Database-backed API Keys**: SQLite storage for persistent API key management
- **Rate Limiting**: Configurable daily request limits per client
- **Usage Tracking**: Monitor API usage and token consumption
- **Authentication**: Supports both `x-api-key` header and `Authorization: Bearer` token

### 🌐 Web Interface
- **Beautiful Dashboard**: Real-time statistics and system monitoring
- **API Key Management**: Create, view, and manage client API keys
- **Interactive Chat**: Web-based chat interface with your AI models
- **Modern Design**: Responsive UI with Tailwind CSS and Font Awesome icons

### 🔌 API Compatibility
- **OpenAI-Compatible**: Standard OpenAI API endpoints
- **vLLM Integration**: Seamless proxy to your vLLM backend
- **Streaming Support**: Handles streaming and non-streaming responses
- **Error Handling**: Comprehensive error handling and logging

## 📁 File Structure

```
vllm_gateway/
├── gateway.py              # Main production gateway server
├── requirements.txt        # Python dependencies
├── start_production.sh    # Production startup script
├── templates/             # Web interface templates
│   ├── home.html         # Landing page
│   ├── dashboard.html    # Admin dashboard
│   ├── api_keys.html     # API key management
│   └── chat.html         # AI chat interface
└── README.md             # This file
```

## 🌐 Web Interface

### 🏠 Home Page (`/`)
- Modern landing page with live statistics
- Feature highlights and quick access links
- Professional design with gradients and icons

### 📊 Dashboard (`/dashboard`)
- Real-time API key statistics
- System status monitoring
- Quick action buttons for key management
- Recent activity tracking

### 🔑 API Keys Management (`/api/keys`)
- Create new API keys with custom names and rate limits
- View existing keys and usage statistics
- Copy API keys to clipboard
- Delete inactive keys

### 💬 Chat Interface (`/chat`)
- Interactive chat with your AI models
- Model selection dropdown
- Real-time message display
- Configurable parameters (max tokens, temperature)

## 🔧 Configuration

### Environment Variables

```bash
export VLLM_URL="http://localhost:8000/v1"      # vLLM backend URL
export VLLM_API_KEY="supersecretkey"            # Your vLLM API key
export DATABASE_PATH="./gateway.db"              # SQLite database path
export GATEWAY_PORT="8001"                      # Gateway port
```

### Database

The gateway automatically creates a SQLite database for:
- API key storage and management
- Usage tracking and rate limiting
- Request logging and statistics

## 📱 Usage Examples

### Web Interface

1. **Create an API Key**:
   - Go to http://localhost:8001/api/keys
   - Click "Create New API Key"
   - Enter name, email (optional), and rate limit
   - Copy the generated key

2. **Use the Chat Interface**:
   - Go to http://localhost:8001/chat
   - Enter your API key
   - Select a model from the dropdown
   - Start chatting with your AI models!

### API Usage

```bash
# Get available models
curl -H "x-api-key: YOUR_API_KEY" http://localhost:8001/v1/models

# Chat completion
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "x-api-key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta-llama/Llama-3.2-1B-Instruct",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 100
  }'

# Text completion
curl -X POST http://localhost:8001/v1/completions \
  -H "x-api-key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta-llama/Llama-3.2-1B-Instruct",
    "prompt": "The future of AI is",
    "max_tokens": 50
  }'
```

### Python Client

```python
import requests

# Initialize client
api_key = "YOUR_API_KEY"
base_url = "http://localhost:8001"

# Get models
response = requests.get(f"{base_url}/v1/models", headers={"x-api-key": api_key})
models = response.json()

# Chat completion
response = requests.post(
    f"{base_url}/v1/chat/completions",
    headers={"x-api-key": api_key, "Content-Type": "application/json"},
    json={
        "model": "meta-llama/Llama-3.2-1B-Instruct",
        "messages": [{"role": "user", "content": "Hello!"}],
        "max_tokens": 100
    }
)
result = response.json()
print(result['choices'][0]['message']['content'])
```

## 🚨 Security Features

1. **API Key Protection**: Your vLLM API key is never exposed to clients
2. **Rate Limiting**: Configurable daily limits per client
3. **Usage Tracking**: Monitor and log all API usage
4. **Authentication Required**: All endpoints require valid API keys
5. **Database Security**: SQLite database with proper access controls

## 🔄 Production Deployment

### Quick Start Script

```bash
# Make the script executable
chmod +x start_production.sh

# Start the production gateway
./start_production.sh
```

### Manual Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start the gateway
python gateway.py
```

### Environment Setup

```bash
# Set environment variables
export VLLM_URL="http://localhost:8000/v1"
export VLLM_API_KEY="your_super_secret_key"
export DATABASE_PATH="./gateway.db"
export GATEWAY_PORT="8001"

# Start the gateway
python gateway.py
```

## 🐛 Troubleshooting

### Common Issues

1. **Port conflicts**: Ensure ports 8000 (vLLM) and 8001 (gateway) are available
2. **Authentication errors**: Verify your API key is correct and active
3. **Connection errors**: Ensure vLLM backend is running on port 8000
4. **Database errors**: Check file permissions for the SQLite database

### Logs and Debugging

```bash
# Start gateway with verbose logging
python gateway.py

# Check gateway logs for errors
# Look for 401 (unauthorized) vs 500 (server error) responses
```

### API Key Issues

- **401 Unauthorized**: Invalid or missing API key
- **Rate Limit Exceeded**: Daily limit reached for your API key
- **Model Not Found**: Check if the model ID is correct

## 📚 API Reference

The gateway implements standard OpenAI-compatible endpoints:

- **GET /v1/models** - List available models
- **POST /v1/chat/completions** - Chat completions
- **POST /v1/completions** - Text completions

### Authentication Headers

```bash
# Method 1: x-api-key header
x-api-key: YOUR_API_KEY

# Method 2: Authorization header
Authorization: Bearer YOUR_API_KEY
```

### Response Format

All responses follow the OpenAI API format:

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "meta-llama/Llama-3.2-1B-Instruct",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "AI response here"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 20,
    "total_tokens": 30
  }
}
```

## 🎯 Use Cases

- **Multi-tenant AI services** with client-specific API keys
- **AI model access control** for organizations
- **Usage monitoring and billing** for AI services
- **Secure AI model deployment** in production environments
- **Client application integration** with controlled access

## 🤝 Contributing

Feel free to submit issues and enhancement requests!

## 📄 License

This project is open source and available under the MIT License.

---

**🎉 Your vLLM Gateway is now production-ready with a beautiful web interface!**


