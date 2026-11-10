#!/bin/bash

# Function to handle cleanup on exit
cleanup() {
    echo "Stopping all services..."
    kill $(jobs -p) 2>/dev/null
    echo "All services stopped."
}

# Trap SIGINT (Ctrl+C) and call cleanup
trap cleanup SIGINT

# Obtener la ruta del directorio raíz del proyecto
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# ── Entornos ────────────────────────────────────────────────────────────────
# Los tres servicios usan venvs aislados. Si falta alguno, se crean.
if [ ! -x "api/tarea2/bin/python" ] \
   || [ ! -x "agent_app/backend/backend_venv/bin/python" ] \
   || [ ! -x "agent_app/frontend/frontend_venv/bin/python" ]; then
    echo "Faltan entornos virtuales. Ejecutando scripts/bootstrap_envs.sh..."
    ./scripts/bootstrap_envs.sh || { echo "No se pudieron crear los entornos."; exit 1; }
fi

API_PY="api/tarea2/bin/python"
AGENT_PY="agent_app/backend/backend_venv/bin/python"
FRONTEND_PY="agent_app/frontend/frontend_venv/bin/python"
FRONTEND_STREAMLIT="agent_app/frontend/frontend_venv/bin/streamlit"

echo "Starting Support Ticket System..."

# Start API (Part 1)
echo "Starting API on port 8000..."
cd "$PROJECT_ROOT/api"
export PYTHONPATH="$PROJECT_ROOT/api"
echo "PYTHONPATH set to: $PYTHONPATH"
"$PROJECT_ROOT/$API_PY" main.py &
API_PID=$!
cd "$PROJECT_ROOT"

# Wait a moment for API to initialize
sleep 3

# Start Agent Backend (Part 2)
echo "Starting Agent Backend on port 8001..."
cd "$PROJECT_ROOT/agent_app/backend"
export PYTHONPATH="$PROJECT_ROOT/agent_app/backend:$PYTHONPATH"
"$PROJECT_ROOT/$AGENT_PY" main.py &
AGENT_BACKEND_PID=$!
cd "$PROJECT_ROOT"

# Wait a moment for Agent Backend to initialize
sleep 3

# Start Streamlit Frontend (Part 2)
echo "Starting Streamlit Frontend..."
cd "$PROJECT_ROOT/agent_app/frontend"
export PYTHONPATH="$PROJECT_ROOT/agent_app/backend:$PYTHONPATH"
"$PROJECT_ROOT/$FRONTEND_STREAMLIT" run app.py &
FRONTEND_PID=$!
cd "$PROJECT_ROOT"

echo "All services are running."
echo "Press Ctrl+C to stop all services."

# Wait for all background processes
wait
