#!/usr/bin/env python3
"""
Simple Load Balancer for vLLM Gateway
Distributes requests across multiple gateway instances
"""

import asyncio
import json
import logging
import random
import time
from typing import List, Dict, Any
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="vLLM Load Balancer", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LoadBalancer:
    def __init__(self):
        self.gateways = [
            "http://localhost:8001",
            "http://localhost:8002", 
            "http://localhost:8003"
        ]
        self.health_status = {gateway: True for gateway in self.gateways}
        self.request_counts = {gateway: 0 for gateway in self.gateways}
        self.last_health_check = {gateway: 0 for gateway in self.gateways}
        self.health_check_interval = 30  # seconds
        
    async def health_check(self, gateway: str) -> bool:
        """Check if a gateway is healthy"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{gateway}/health")
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Health check failed for {gateway}: {e}")
            return False
    
    async def update_health_status(self):
        """Update health status of all gateways"""
        current_time = time.time()
        
        for gateway in self.gateways:
            # Only check if enough time has passed
            if current_time - self.last_health_check[gateway] > self.health_check_interval:
                self.health_status[gateway] = await self.health_check(gateway)
                self.last_health_check[gateway] = current_time
                
                if not self.health_status[gateway]:
                    logger.warning(f"Gateway {gateway} is unhealthy")
                else:
                    logger.info(f"Gateway {gateway} is healthy")
    
    def get_healthy_gateways(self) -> List[str]:
        """Get list of healthy gateways"""
        return [gateway for gateway in self.gateways if self.health_status[gateway]]
    
    def select_gateway(self, strategy: str = "round_robin") -> str:
        """Select a gateway using the specified strategy"""
        healthy_gateways = self.get_healthy_gateways()
        
        if not healthy_gateways:
            raise HTTPException(status_code=503, detail="No healthy gateways available")
        
        if strategy == "round_robin":
            # Round-robin selection
            selected = min(healthy_gateways, key=lambda g: self.request_counts[g])
            self.request_counts[selected] += 1
            return selected
        
        elif strategy == "random":
            # Random selection
            return random.choice(healthy_gateways)
        
        elif strategy == "least_connections":
            # Least connections selection
            selected = min(healthy_gateways, key=lambda g: self.request_counts[g])
            self.request_counts[selected] += 1
            return selected
        
        else:
            # Default to round-robin
            selected = min(healthy_gateways, key=lambda g: self.request_counts[g])
            self.request_counts[selected] += 1
            return selected

# Initialize load balancer
lb = LoadBalancer()

@app.on_event("startup")
async def startup_event():
    """Initialize load balancer on startup"""
    logger.info("Load balancer starting up...")
    await lb.update_health_status()

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Load balancer shutting down...")

@app.get("/health")
async def health_check():
    """Health check endpoint for the load balancer"""
    await lb.update_health_status()
    healthy_count = len(lb.get_healthy_gateways())
    total_count = len(lb.gateways)
    
    return {
        "status": "healthy" if healthy_count > 0 else "unhealthy",
        "healthy_gateways": healthy_count,
        "total_gateways": total_count,
        "gateways": [
            {
                "url": gateway,
                "healthy": lb.health_status[gateway],
                "request_count": lb.request_counts[gateway]
            }
            for gateway in lb.gateways
        ]
    }

@app.get("/stats")
async def get_stats():
    """Get load balancer statistics"""
    await lb.update_health_status()
    
    return {
        "total_requests": sum(lb.request_counts.values()),
        "gateway_stats": [
            {
                "url": gateway,
                "healthy": lb.health_status[gateway],
                "request_count": lb.request_counts[gateway],
                "last_health_check": lb.last_health_check[gateway]
            }
            for gateway in lb.gateways
        ]
    }

async def proxy_request(request: Request, gateway: str, path: str):
    """Proxy request to a specific gateway"""
    # Reconstruct the full URL
    full_url = f"{gateway}{path}"
    
    # Get request body
    body = await request.body()
    
    # Prepare headers
    headers = dict(request.headers)
    # Remove host header to avoid conflicts
    headers.pop("host", None)
    
    # Make request to gateway
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.request(
                method=request.method,
                url=full_url,
                headers=headers,
                content=body,
                params=request.query_params
            )
            
            # Return response
            return StreamingResponse(
                content=response.aiter_bytes(),
                status_code=response.status_code,
                headers=dict(response.headers)
            )
            
        except Exception as e:
            logger.error(f"Error proxying to {gateway}: {e}")
            raise HTTPException(status_code=502, detail=f"Gateway error: {str(e)}")

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_all(request: Request, path: str):
    """Proxy all requests to healthy gateways"""
    await lb.update_health_status()
    
    try:
        # Select a healthy gateway
        selected_gateway = lb.select_gateway(strategy="round_robin")
        logger.info(f"Routing request to {selected_gateway}")
        
        # Proxy the request
        return await proxy_request(request, selected_gateway, f"/{path}")
        
    except Exception as e:
        logger.error(f"Load balancer error: {e}")
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting vLLM Load Balancer on port 8080")
    uvicorn.run(app, host="0.0.0.0", port=8080)
