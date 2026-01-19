import streamlit as st
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

API_MAIN_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
AGENT_BACKEND_URL = "http://localhost:8001"

st.set_page_config(page_title="Agente de Resolución de Tickets", page_icon="🤖", layout="wide")

# --- Session State Initialization ---
if 'token' not in st.session_state:
    st.session_state['token'] = None
if 'username' not in st.session_state:
    st.session_state['username'] = None

def logout():
    st.session_state['token'] = None
    st.session_state['username'] = None
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

st.title("🤖 Agente de Resolución de Tickets")
st.markdown("""
Este agente inteligente te ayuda a resolver tickets de soporte técnico utilizando RAG y búsqueda web.
""")

col1, col2 = st.columns([1, 1])

with col1:
    ticket_json_input = st.text_area(
        "Pega el JSON del Ticket aquí:",
        height=400,
        placeholder='''{
      "ticketId": "12345",
      "title": "Error de conexión en base de datos",
      "description": "El servidor no puede conectar a MongoDB Atlas después del reinicio."
    }'''
    )

    if st.button("🚀 Resolver Ticket"):
        if not ticket_json_input:
            st.error("Por favor, ingresa el JSON del ticket.")
        else:
            try:
                ticket_data = json.loads(ticket_json_input)
                
                with st.spinner("El agente está analizando el caso..."):
                    headers = {"Authorization": f"Bearer {st.session_state['token']}"}
                    response = requests.post(
                        f"{AGENT_BACKEND_URL}/solve_ticket",
                        json={"ticket": ticket_data},
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        st.session_state['last_solution'] = response.json().get("solution")
                    else:
                        st.error(f"Error ({response.status_code}): {response.text}")
                        
            except json.JSONDecodeError:
                st.error("Formato JSON inválido.")
            except Exception as e:
                st.error(f"Error inesperado: {str(e)}")

with col2:
    st.markdown("### 💡 Solución Propuesta")
    if 'last_solution' in st.session_state and st.session_state['last_solution']:
        st.markdown(st.session_state['last_solution'])
    else:
        st.info("Ingresa un ticket y haz clic en 'Resolver' para ver la propuesta del agente.")
