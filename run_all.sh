#!/bin/bash

# Function to handle cleanup on exit
cleanup() {
    echo "Stopping all services..."
    kill $(jobs -p)
    echo "All services stopped."
}

# Trap SIGINT (Ctrl+C) and call cleanup
trap cleanup SIGINT

echo "Starting Support Ticket System..."

# Start API (Part 1)
echo "Starting API on port 8000..."
cd api
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d "tarea2" ]; then
    source tarea2/bin/activate
elif [ -d "../venv" ]; then
    source ../venv/bin/activate
fi
# Using python3 main.py as observed in usage history, or fallback to uvicorn if main.py doesn't setup the server similarly
python3 main.py &
API_PID=$!
cd ..

# Wait a moment for API to initialize
sleep 3

# Start Agent Backend (Part 2)
echo "Starting Agent Backend on port 8001..."
cd agent_app/backend
# Try to activate agent venv if it exists in expected locations
if [ -d "../agente_venv" ]; then
    source "../agente_venv/bin/activate"
elif [ -d "../../agente_venv" ]; then
    source "../../agente_venv/bin/activate"
fi
python3 main.py &
AGENT_BACKEND_PID=$!
cd ../..

# Wait a moment for Agent Backend to initialize
sleep 3

# Start Streamlit Frontend (Part 2)
echo "Starting Streamlit Frontend..."
cd agent_app/frontend
# Ensure we are still in the agent venv or reactivate just in case (subshells usually handle this but cd changes context)
if [ -d "../agente_venv" ]; then
    source "../agente_venv/bin/activate"
fi
streamlit run app.py &
FRONTEND_PID=$!
cd ../..

echo "All services are running."
echo "Press Ctrl+C to stop all services."

# Wait for all background processes
wait
