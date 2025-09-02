#!/bin/bash

echo "🚀 Starting vLLM Gateway with Load Balancer"
echo "============================================="
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "Please run ./setup_env.sh first to create your .env file."
    exit 1
fi

# Load environment variables
source .env

# Create logs directory
mkdir -p logs

# Function to start a gateway instance
start_gateway() {
    local port=$1
    local db_name="gateway${port}.db"
    
    echo "🚀 Starting Gateway on port $port with database $db_name"
    
    # Set instance-specific environment variables
    export GATEWAY_PORT=$port
    export DATABASE_PATH="./$db_name"
    
    # Start gateway in background
    python3 gateway.py > "logs/gateway_${port}.log" 2>&1 &
    
    # Store PID for cleanup
    echo $! > "logs/gateway_${port}.pid"
    
    echo "✅ Gateway $port started with PID $(cat logs/gateway_${port}.pid)"
}

# Function to start load balancer
start_load_balancer() {
    echo "🌐 Starting Load Balancer on port 8080"
    
    # Start load balancer in background
    python3 load_balancer.py > "logs/load_balancer.log" 2>&1 &
    
    # Store PID for cleanup
    echo $! > "logs/load_balancer.pid"
    
    echo "✅ Load Balancer started with PID $(cat logs/load_balancer.pid)"
}

# Function to stop all services
stop_services() {
    echo ""
    echo "🛑 Stopping all services..."
    
    # Stop load balancer
    if [ -f "logs/load_balancer.pid" ]; then
        local pid=$(cat "logs/load_balancer.pid")
        echo "Stopping load balancer with PID $pid"
        kill $pid 2>/dev/null || true
        rm "logs/load_balancer.pid"
    fi
    
    # Stop gateways
    for pid_file in logs/gateway_*.pid; do
        if [ -f "$pid_file" ]; then
            local pid=$(cat "$pid_file")
            echo "Stopping gateway with PID $pid"
            kill $pid 2>/dev/null || true
            rm "$pid_file"
        fi
    done
    
    echo "✅ All services stopped"
}

# Trap to stop services on script exit
trap stop_services EXIT

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Start multiple gateway instances
echo ""
echo "🚀 Starting gateway instances..."

# Start 3 gateway instances on different ports
start_gateway 8001
sleep 3
start_gateway 8002
sleep 3
start_gateway 8003

echo ""
echo "⏳ Waiting for gateways to start..."
sleep 8

# Check if all gateways are running
echo ""
echo "🔍 Checking gateway status..."

for port in 8001 8002 8003; do
    if curl -s "http://localhost:$port/health" > /dev/null 2>&1; then
        echo "✅ Gateway $port: HEALTHY"
    else
        echo "❌ Gateway $port: UNHEALTHY"
    fi
done

# Start load balancer
echo ""
start_load_balancer

echo ""
echo "⏳ Waiting for load balancer to start..."
sleep 5

# Check load balancer status
echo ""
echo "🔍 Checking load balancer status..."

if curl -s "http://localhost:8080/health" > /dev/null 2>&1; then
    echo "✅ Load Balancer: HEALTHY"
    
    # Show load balancer stats
    echo ""
    echo "📊 Load Balancer Statistics:"
    curl -s "http://localhost:8080/stats" | python3 -m json.tool 2>/dev/null || echo "Could not fetch stats"
else
    echo "❌ Load Balancer: UNHEALTHY"
fi

echo ""
echo "🎯 Load Balanced System Setup Complete!"
echo ""
echo "📊 Service Endpoints:"
echo "   - Gateway 1: http://localhost:8001"
echo "   - Gateway 2: http://localhost:8002"
echo "   - Gateway 3: http://localhost:8003"
echo "   - Load Balancer: http://localhost:8080"
echo ""
echo "🌐 Access your applications through the load balancer:"
echo "   - Web Interface: http://localhost:8080"
echo "   - API Endpoints: http://localhost:8080/v1/*"
echo "   - Health Check: http://localhost:8080/health"
echo "   - Statistics: http://localhost:8080/stats"
echo ""
echo "📝 Logs are available in the logs/ directory"
echo "🛑 Press Ctrl+C to stop all services"
echo ""

# Wait for user to stop
wait
