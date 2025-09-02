import os
import sqlite3
import hashlib
import secrets
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Request, HTTPException, Depends, Header
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import httpx
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI(
    title="vLLM Gateway",
    description="A secure gateway for vLLM API access",
    version="1.0.0"
)

# Configuration from environment variables
VLLM_URL = os.getenv("VLLM_URL", "http://localhost:8000/v1")
VLLM_API_KEY = os.getenv("VLLM_API_KEY", "supersecretkey")  # Fallback for development
DATABASE_PATH = os.getenv("DATABASE_PATH", "./gateway.db")
GATEWAY_PORT = int(os.getenv("GATEWAY_PORT", "8001"))

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates for frontend
templates = Jinja2Templates(directory="templates")

# Database setup
def init_database():
    """Initialize the database with required tables"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # API Keys table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_keys (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT,
            api_key TEXT UNIQUE NOT NULL,
            rate_limit INTEGER DEFAULT 100,
            daily_usage INTEGER DEFAULT 0,
            last_used TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    # Usage tracking table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usage_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_key_id TEXT,
            endpoint TEXT,
            tokens_used INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (api_key_id) REFERENCES api_keys (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def get_db_connection():
    """Get database connection"""
    return sqlite3.connect(DATABASE_PATH)

def hash_api_key(api_key: str) -> str:
    """Hash API key for storage"""
    return hashlib.sha256(api_key.encode()).hexdigest()

def generate_api_key() -> str:
    """Generate a new API key"""
    return f"vllm_{secrets.token_urlsafe(32)}"

def validate_api_key(api_key: str) -> Optional[Dict[str, Any]]:
    """Validate API key and return user info"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, name, email, rate_limit, daily_usage, is_active 
        FROM api_keys 
        WHERE api_key = ? AND is_active = 1
    ''', (api_key,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            "id": result[0],
            "name": result[1],
            "email": result[2],
            "rate_limit": result[3],
            "daily_usage": result[4]
        }
    return None

def check_rate_limit(api_key: str) -> bool:
    """Check if API key is within rate limits"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check daily usage
    cursor.execute('''
        SELECT rate_limit, daily_usage 
        FROM api_keys 
        WHERE api_key = ?
    ''', (api_key,))
    
    result = cursor.fetchone()
    if not result:
        conn.close()
        return False
    
    rate_limit, daily_usage = result
    
    # Reset daily usage if it's a new day
    cursor.execute('''
        SELECT last_used FROM api_keys WHERE api_key = ?
    ''', (api_key,))
    
    last_used = cursor.fetchone()
    if last_used and last_used[0]:
        last_used_date = datetime.fromisoformat(last_used[0])
        if last_used_date.date() < datetime.now().date():
            # Reset daily usage for new day
            cursor.execute('''
                UPDATE api_keys SET daily_usage = 0 WHERE api_key = ?
            ''', (api_key,))
            daily_usage = 0
    
    conn.commit()
    conn.close()
    
    return daily_usage < rate_limit

def log_usage(api_key: str, endpoint: str, tokens_used: int):
    """Log API usage"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Update daily usage
    cursor.execute('''
        UPDATE api_keys 
        SET daily_usage = daily_usage + ?, last_used = CURRENT_TIMESTAMP 
        WHERE api_key = ?
    ''', (tokens_used, api_key))
    
    # Log usage
    cursor.execute('''
        INSERT INTO usage_logs (api_key_id, endpoint, tokens_used, timestamp)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    ''', (api_key, endpoint, tokens_used))
    
    conn.commit()
    conn.close()

def get_client_key(request: Request) -> Optional[str]:
    """Extract client API key from request headers"""
    client_key = request.headers.get("x-api-key")
    
    if not client_key:
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            client_key = auth_header.replace("Bearer ", "").strip()
    
    return client_key

def validate_and_check_rate_limit(request: Request) -> Dict[str, Any]:
    """Validate API key and check rate limits"""
    client_key = get_client_key(request)
    
    if not client_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Use x-api-key header or Authorization: Bearer"
        )
    
    user_info = validate_api_key(client_key)
    if not user_info:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    
    if not check_rate_limit(client_key):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Try again tomorrow."
        )
    
    return user_info

# Frontend routes
@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    """Home page with landing content"""
    # Get basic stats for the home page
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) as total, SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active FROM api_keys')
        result = cursor.fetchone()
        
        total_keys = result[0] if result else 0
        active_keys = result[1] if result else 0
        
        # Get today's usage
        cursor.execute('SELECT SUM(daily_usage) as today_usage FROM api_keys')
        today_result = cursor.fetchone()
        today_requests = today_result[0] if today_result and today_result[0] else 0
        
        conn.close()
        
        stats = {
            "totalKeys": total_keys,
            "activeKeys": active_keys,
            "todayRequests": today_requests,
            "totalTokens": today_requests  # For now, using same as requests
        }
    except Exception as e:
        # If database error, provide default stats
        stats = {
            "totalKeys": 0,
            "activeKeys": 0,
            "todayRequests": 0,
            "totalTokens": 0
        }
    
    return templates.TemplateResponse("home.html", {"request": request, "stats": stats})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard for API key management"""
    # Get stats for the dashboard
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) as total, SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active FROM api_keys')
        result = cursor.fetchone()
        
        total_keys = result[0] if result else 0
        active_keys = result[1] if result else 0
        
        # Get today's usage
        cursor.execute('SELECT SUM(daily_usage) as today_usage FROM api_keys')
        today_result = cursor.fetchone()
        today_requests = today_result[0] if today_result and today_result[0] else 0
        
        conn.close()
        
        stats = {
            "totalKeys": total_keys,
            "activeKeys": active_keys,
            "todayRequests": today_requests,
            "totalTokens": today_requests  # For now, using same as requests
        }
    except Exception as e:
        # If database error, provide default stats
        stats = {
            "totalKeys": 0,
            "activeKeys": 0,
            "todayRequests": 0,
            "totalTokens": 0
        }
    
    return templates.TemplateResponse("dashboard.html", {"request": request, "stats": stats})

@app.get("/api/keys", response_class=HTMLResponse)
async def api_keys_page(request: Request):
    """API keys management page"""
    # Get API keys for the template
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, email, api_key, rate_limit, daily_usage, last_used, created_at, is_active
            FROM api_keys
            ORDER BY created_at DESC
        ''')
        
        keys = []
        for row in cursor.fetchall():
            keys.append({
                "id": row[0],
                "name": row[1],
                "email": row[2],
                "api_key": row[3],
                "rate_limit": row[4],
                "daily_usage": row[5],
                "last_used": row[6],
                "created_at": row[7],
                "is_active": bool(row[8])
            })
        
        conn.close()
    except Exception as e:
        keys = []
    
    return templates.TemplateResponse("api_keys.html", {"request": request, "api_keys": keys})

@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    """Chat application page"""
    # For now, pass empty data - the chat will load models via JavaScript
    return templates.TemplateResponse("chat.html", {"request": request})

@app.get("/docs")
async def docs_redirect():
    """Redirect to API documentation"""
    return StreamingResponse(content=b"Redirecting to API documentation...", media_type="text/plain")

# API endpoints
@app.get("/api/v1/keys")
async def list_api_keys():
    """List all API keys (admin endpoint)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, name, email, api_key, rate_limit, daily_usage, last_used, created_at, is_active
        FROM api_keys
        ORDER BY created_at DESC
    ''')
    
    keys = []
    for row in cursor.fetchall():
        keys.append({
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "api_key": row[3],
            "rate_limit": row[4],
            "daily_usage": row[5],
            "last_used": row[6],
            "created_at": row[7],
            "is_active": bool(row[8])
        })
    
    conn.close()
    return {"keys": keys}

@app.post("/api/v1/keys")
async def create_api_key(request: Request):
    """Create a new API key"""
    data = await request.json()
    name = data.get("name", "Unnamed Key")
    email = data.get("email", "")
    rate_limit = data.get("rate_limit", 100)
    
    api_key = generate_api_key()
    key_id = str(uuid.uuid4())
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO api_keys (id, name, email, api_key, rate_limit)
        VALUES (?, ?, ?, ?, ?)
    ''', (key_id, name, email, api_key, rate_limit))
    
    conn.commit()
    conn.close()
    
    return {
        "id": key_id,
        "name": name,
        "email": email,
        "api_key": api_key,
        "rate_limit": rate_limit,
        "message": "API key created successfully"
    }

@app.delete("/api/v1/keys/{key_id}")
async def delete_api_key(key_id: str):
    """Delete an API key"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM api_keys WHERE id = ?', (key_id,))
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="API key not found")
    
    conn.commit()
    conn.close()
    
    return {"message": "API key deleted successfully"}

# vLLM proxy endpoints
@app.get("/v1/models")
async def get_models(request: Request):
    """Get available models from vLLM"""
    user_info = validate_and_check_rate_limit(request)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{VLLM_URL}/models",
                headers={"Authorization": f"Bearer {VLLM_API_KEY}"},
                timeout=30.0
            )
            
            # Log usage
            log_usage(user_info["id"], "/v1/models", 0)
            
            return JSONResponse(
                status_code=response.status_code,
                content=response.json()
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error connecting to vLLM: {str(e)}")

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """Handle chat completions"""
    user_info = validate_and_check_rate_limit(request)
    body = await request.body()
    
    try:
        request_data = json.loads(body)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{VLLM_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {VLLM_API_KEY}",
                    "Content-Type": "application/json"
                },
                content=body,
                timeout=60.0
            )
            
            response_data = response.json()
            
            # Log usage (estimate tokens)
            tokens_used = len(str(request_data)) // 4 + len(str(response_data)) // 4
            log_usage(user_info["id"], "/v1/chat/completions", tokens_used)
            
            return JSONResponse(
                status_code=response.status_code,
                content=response_data
            )
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error connecting to vLLM: {str(e)}")

@app.post("/v1/completions")
async def completions(request: Request):
    """Handle text completions"""
    user_info = validate_and_check_rate_limit(request)
    body = await request.body()
    
    try:
        request_data = json.loads(body)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{VLLM_URL}/completions",
                headers={
                    "Authorization": f"Bearer {VLLM_API_KEY}",
                    "Content-Type": "application/json"
                },
                content=body,
                timeout=60.0
            )
            
            response_data = response.json()
            
            # Log usage
            tokens_used = len(str(request_data)) // 4 + len(str(response_data)) // 4
            log_usage(user_info["id"], "/v1/completions", tokens_used)
            
            return JSONResponse(
                status_code=response.status_code,
                content=response_data
            )
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error connecting to vLLM: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint for load balancer"""
    try:
        # Check database connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        conn.close()
        
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")

@app.get("/monitor")
async def monitor_page(request: Request):
    """Monitor page for load balancer and gateway statistics"""
    return templates.TemplateResponse("monitor.html", {"request": request})

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_database()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=GATEWAY_PORT)
