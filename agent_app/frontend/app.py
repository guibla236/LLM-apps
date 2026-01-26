import streamlit as st
import requests
import os
import uuid
import time
from dotenv import load_dotenv
import extra_streamlit_components as stx

load_dotenv()

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

# --- Custom CSS for Toast Positioning ---
st.markdown("""
<style>
    /* Move toast to bottom center */
    div[data-testid="stToast"] {
        position: fixed;
        bottom: 50px !important;
        left: 50% !important;
        transform: translateX(-50%) !important;
        right: auto !important;
        top: auto !important;
        width: auto !important;
        min-width: 200px;
    }
</style>
""", unsafe_allow_html=True)

# --- Cookie Manager for Persistence ---
cookie_manager = stx.CookieManager()

# --- Session State Initialization ---
if 'token' not in st.session_state:
    st.session_state['token'] = None
if 'username' not in st.session_state:
    st.session_state['username'] = None
if 'messages' not in st.session_state:
    st.session_state['messages'] = []
if 'chat_session_id' not in st.session_state:
    st.session_state['chat_session_id'] = str(uuid.uuid4())

# --- Auto-Login Check (Persistence) ---
# If token not in state, try checking cookie
if not st.session_state['token']:
    try:
        auth_cookie = cookie_manager.get("auth_token")
        if auth_cookie:
            # We have a cookie, let's assume it's valid or validate with /me
            # Validating with /me is safer
            headers = {"Authorization": f"Bearer {auth_cookie}"}
            me_resp = requests.get(f"{API_MAIN_URL}/api/me", headers=headers)
            if me_resp.status_code == 200:
                data = me_resp.json()
                st.session_state['token'] = auth_cookie
                st.session_state['username'] = data['username']
                # Optionally rerun to skip login screen immediately
                # st.rerun() 
                # But we are at top level, so falling through to main page logic works if we structure carefully.
                # Since Streamlit runs top-to-bottom, if we set token here, the login block below won't trigger.
            else:
                # Invalid cookie
                cookie_manager.delete("auth_token")
    except Exception as e:
        pass

def logout():
    st.session_state['token'] = None
    st.session_state['username'] = None
    st.session_state['messages'] = []
    st.session_state['chat_session_id'] = str(uuid.uuid4())
    # Delete cookie
    cookie_manager.delete("auth_token")
    st.rerun()

# --- Login Logic ---
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
                    token = data['access_token']
                    st.session_state['token'] = token
                    st.session_state['username'] = data['username']
                    
                    # Set persistent cookie (expires in 7 days by default if not specified, or session)
                    cookie_manager.set("auth_token", token)
                    
                    st.success("¡Ingreso exitoso!")
                    time.sleep(1) # Wait for cookie to set
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
            
            # --- Empty State Message ---
            if not sessions:
                st.sidebar.info("No hay historial.")
            
            for s in sessions:
                # s is now a dict: {session_id, thread_id, title, last_updated}
                title = s.get("title", "Chat")
                session_id = s.get("session_id")
                
                # Truncate title quite strictly (12 chars) to ensure single line with trash icon
                display_text = (title[:12] + '...') if len(title) > 12 else title
                
                # 'help' parameter for tooltip (works as a hover text in newer Streamlit versions)
                col1, col2 = st.sidebar.columns([0.8, 0.2])
                with col1:
                    if st.button(display_text, key=session_id, help=title):
                        st.session_state['chat_session_id'] = session_id
                        # Load history
                        hist_resp = requests.get(f"{AGENT_BACKEND_URL}/history/{session_id}", headers=headers)
                        if hist_resp.status_code == 200:
                            st.session_state['messages'] = hist_resp.json().get("messages", [])
                        st.rerun()
                
                with col2:
                    if st.button("🗑️", key=f"del_{session_id}", help="Eliminar conversación"):
                        # Delete session
                        del_headers = {"Authorization": f"Bearer {st.session_state['token']}"}
                        try:
                            requests.delete(f"{AGENT_BACKEND_URL}/history/{session_id}", headers=del_headers)
                            
                            # If we deleted the active session, reset view
                            if st.session_state.get('chat_session_id') == session_id:
                                st.session_state['messages'] = []
                                st.session_state['chat_session_id'] = str(uuid.uuid4())
                            
                            st.toast("Conversación eliminada correctamente! 🗑️")
                            time.sleep(2) # Give time for toast to show
                            st.rerun()
                        except Exception as e:
                            st.sidebar.error(f"Error deleting: {e}")
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
