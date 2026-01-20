import streamlit as st
import requests
import json
import os
import uuid
from dotenv import load_dotenv

load_dotenv()

# ... (get_config and API URLs remain same)
def get_config(key, default):
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        # Streamlit raises StreamlitSecretNotFoundError if no secrets are found
        pass
    return os.getenv(key, default)

API_MAIN_URL = get_config("API_MAIN_URL", os.getenv("API_BASE_URL", "http://localhost:8000"))
AGENT_BACKEND_URL = get_config("API_AGENT_URL", "http://localhost:8001")

st.set_page_config(page_title="Agente de Resolución de Tickets", page_icon="🤖", layout="wide")

# --- Session State Initialization ---
if 'token' not in st.session_state:
    st.session_state['token'] = None
if 'username' not in st.session_state:
    st.session_state['username'] = None
if 'messages' not in st.session_state:
    st.session_state['messages'] = []
if 'chat_session_id' not in st.session_state:
    st.session_state['chat_session_id'] = str(uuid.uuid4())

def logout():
    st.session_state['token'] = None
    st.session_state['username'] = None
    st.session_state['messages'] = []
    st.session_state['chat_session_id'] = str(uuid.uuid4())
    st.rerun()

# --- Login Logic ---
# ... (existing login logic is fine)
if not st.session_state['token']:
    st.title("🔐 Ingreso al Sistema de Agente")
    
    with st.form("login_form"):
        username = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        submit = st.form_submit_button("Ingresar")
        
        if submit:
            try:
                response = requests.post(
                    f"{API_MAIN_URL}/api/login",
                    json={"username": username, "password": password}
                )
                if response.status_code == 200:
                    data = response.json()
                    st.session_state['token'] = data['access_token']
                    st.session_state['username'] = data['username']
                    st.success("¡Ingreso exitoso!")
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas")
            except Exception as e:
                st.error(f"Error de conexión: {str(e)}")
    st.stop()

# --- Main Page After Login ---
st.sidebar.title(f"👤 {st.session_state['username']}")
if st.sidebar.button("Cerrar Sesión"):
    logout()

st.sidebar.markdown("---")
# New Conversation Button
if st.sidebar.button("➕ Nueva Conversación"):
    st.session_state['messages'] = []
    st.session_state['chat_session_id'] = str(uuid.uuid4())
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("📜 Historial")

# Load past sessions
if st.session_state['token']:
    try:
        headers = {"Authorization": f"Bearer {st.session_state['token']}"}
        resp = requests.get(f"{AGENT_BACKEND_URL}/sessions", headers=headers)
        if resp.status_code == 200:
            sessions = resp.json().get("sessions", [])
            for s in sessions:
                # s is now a dict: {session_id, thread_id, title, last_updated}
                title = s.get("title", "Chat")
                session_id = s.get("session_id")
                
                # Truncate title if too long
                display_text = (title[:25] + '...') if len(title) > 25 else title
                
                if st.sidebar.button(display_text, key=session_id):
                    st.session_state['chat_session_id'] = session_id
                    # Load history
                    hist_resp = requests.get(f"{AGENT_BACKEND_URL}/history/{session_id}", headers=headers)
                    if hist_resp.status_code == 200:
                        st.session_state['messages'] = hist_resp.json().get("messages", [])
                    st.rerun()
    except Exception as e:
        st.sidebar.error(f"Connection error: {e}")

st.title("🤖 Chat de Soporte IT")
st.markdown("""
Describe tu problema técnico y el agente te ayudará utilizando la base de conocimientos y búsqueda web.
""")

# Display chat history
for message in st.session_state['messages']:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("¿En qué puedo ayudarte hoy?"):
    # Add user message to state
    st.session_state['messages'].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get response from agent
    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            try:
                headers = {"Authorization": f"Bearer {st.session_state['token']}"}
                response = requests.post(
                    f"{AGENT_BACKEND_URL}/chat",
                    json={
                        "message": prompt, 
                        "session_id": st.session_state['chat_session_id']
                    },
                    headers=headers
                )
                
                if response.status_code == 200:
                    agent_response = response.json().get("response")
                    st.markdown(agent_response)
                    st.session_state['messages'].append({"role": "assistant", "content": agent_response})
                    # Force rerun to update sidebar with new title if it was a new session
                    st.rerun()
                else:
                    st.error(f"Error ({response.status_code}): {response.text}")
            except Exception as e:
                st.error(f"Error inesperado: {str(e)}")
