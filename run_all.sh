#!/bin/bash

# Function to handle cleanup on exit
cleanup() {
    echo "Stopping all services..."
    kill $(jobs -p)
    echo "All services stopped."
}

# Trap SIGINT (Ctrl+C) and call cleanup
trap cleanup SIGINT

# Obtener la ruta del directorio raíz del proyecto
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Starting Support Ticket System..."

# Start API (Part 1)
echo "Starting API on port 8000..."
cd "$PROJECT_ROOT/api"
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d "tarea2" ]; then
    source tarea2/bin/activate
elif [ -d "../venv" ]; then
    source ../venv/bin/activate
fi

# Conffiguration of PYTHONPATH for the API
export PYTHONPATH="$PROJECT_ROOT/api"
echo "PYTHONPATH set to: $PYTHONPATH"

# Execute the API
python3 main.py &
API_PID=$!
cd "$PROJECT_ROOT"

# Wait a moment for API to initialize
sleep 3

# Start Agent Backend (Part 2)
echo "Starting Agent Backend on port 8001..."
cd "$PROJECT_ROOT/agent_app/backend"
if [ -d "backend_venv" ]; then
    source "backend_venv/bin/activate"
fi

# Configuration of PYTHONPATH for the agent's backend
export PYTHONPATH="$PROJECT_ROOT/agent_app/backend:$PYTHONPATH"
python3 main.py &
AGENT_BACKEND_PID=$!
cd "$PROJECT_ROOT"

# Wait a moment for Agent Backend to initialize
sleep 3

# Start Streamlit Frontend (Part 2)
echo "Starting Streamlit Frontend..."
cd "$PROJECT_ROOT/agent_app/frontend"
if [ -d "frontend_venv" ]; then
    source "frontend_venv/bin/activate"
fi

# Configuration of PYTHONPATH for the agent's frontend (note: uses same backend path for imports)
export PYTHONPATH="$PROJECT_ROOT/agent_app/backend:$PYTHONPATH"
streamlit run app.py &
FRONTEND_PID=$!
cd "$PROJECT_ROOT"

echo "All services are running."
echo "Press Ctrl+C to stop all services."

# Wait for all background processes
wait