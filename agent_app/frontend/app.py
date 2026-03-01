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

st.set_page_config(page_title="IT Support Agent System", page_icon="🤖", layout="wide")

# --- Mermaid Graph Helper ---
def render_mermaid(trace):
    """Generates Mermaid code with dynamic tool nodes and path highlighting."""
    if not trace:
        return ""
        
    # Analyze trace to find unique tools used
    tools_used = {} # Mapping sanitized_id -> friendly_name
    visited_ids = set(["Start"])
    
    # Tool labels map
    FRIENDLY_NAMES = {
        "advanced_search_tool": "Advanced Search Tool",
        "search_web_tool": "Web Search"
    }
    
    for step in trace:
        # Identify node type
        if step["node"] == "agent":
             visited_ids.add("Agent")
             if step.get("event") == "answer":
                 visited_ids.add("Final")
        
        # Capture tool usage from EITHER agent thought or tool result
        t_id = step.get("tool_id")
        if t_id:
             # Sanitize ID for Mermaid (no underscores in some older versions, but safer to be alphanumeric)
             clean_id = t_id.replace("_", "")
             visited_ids.add(clean_id)
             if clean_id not in tools_used:
                 label = FRIENDLY_NAMES.get(t_id, t_id)
                 tools_used[clean_id] = label
    
    # Start building Mermaid code
    mermaid_code = """
    graph TD
    Start([Start]) --> Agent[Agent]
    """
    
    # Add tool nodes
    for clean_id, label in tools_used.items():
        mermaid_code += f"\n    Agent --> {clean_id}[{label}]"
        mermaid_code += f"\n    {clean_id} --> Agent"
    
    mermaid_code += "\n    Agent --> Final([Answer])"
    
    # Styles
    mermaid_code += "\n\n    classDef active fill:#28a745,stroke:#28a745,color:#fff;"
    
    # Apply highlighting
    for cid in visited_ids:
        mermaid_code += f"\n    class {cid} active;"
        
    return mermaid_code

def st_mermaid(code: str, unique_id: str):
    import streamlit.components.v1 as components
    clean_code = code.strip()
    
    components.html(
        f"""
        <style>
            body {{ margin: 0; padding: 0; background-color: #0e1117; color: white; font-family: sans-serif; }}
            #mermaid-host {{
                width: 100%;
                height: 400px;
                border: 1px solid #444;
                border-radius: 8px;
                background-color: #0e1117;
                display: flex;
                justify-content: center;
                align-items: center;
                overflow: hidden;
            }}
            #mermaid-svg-container {{
                width: 100%;
                height: 100%;
                display: flex;
                justify-content: center;
                align-items: center;
            }}
            svg {{
                max-width: 90% !important;
                max-height: 380px !important; /* Cap height to prevent blowup */
                width: auto !important;
                height: auto !important;
                margin: auto;
            }}
        </style>
        <div id="mermaid-host">
            <div id="mermaid-svg-container">Esperando al contenedor...</div>
        </div>
        <script type="module">
            import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.esm.min.mjs';
            
            const host = document.getElementById("mermaid-host");
            const target = document.getElementById("mermaid-svg-container");
            let rendered = false;

            const renderGraph = async () => {{
                if (rendered) return;
                try {{
                    mermaid.initialize({{ 
                        startOnLoad: false, 
                        theme: 'dark',
                        securityLevel: 'loose'
                    }});
                    
                    const {{ svg }} = await mermaid.render('render-{unique_id}', `{clean_code}`);
                    target.innerHTML = svg;
                    rendered = true;
                    console.log("Graph rendered for {unique_id}");
                }} catch (e) {{
                    console.error("Render Error:", e);
                    target.innerHTML = "<p style='color:red'>Error al renderizar.</p>";
                }}
            }};

            // Use ResizeObserver to detect when the expander actually opens and provides width/height
            const ro = new ResizeObserver((entries) => {{
                for (let entry of entries) {{
                    if (entry.contentRect.width > 50 && entry.contentRect.height > 50) {{
                        renderGraph();
                        ro.unobserve(host);
                    }}
                }}
            }});
            
            ro.observe(host);
            
            // Safety fallback
            setTimeout(renderGraph, 2000);
        </script>
        """,
        height=420,
    )

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
    st.title("🔐 Login to Agent System")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
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
                    
                    st.success("Login successful!")
                    time.sleep(1) # Wait for cookie to set
                    st.rerun()
                else:
                    st.error("Authentication failed. Please check your credentials.")
            except Exception as e:
                st.error(f"Connection Error: {str(e)}")
    st.stop()

# --- Main Page After Login ---
st.sidebar.title(f"👤 {st.session_state['username']}")
if st.sidebar.button("Logout"):
    logout()

st.sidebar.markdown("---")
# New Conversation Button
if st.sidebar.button("➕ New Conversation"):
    st.session_state['messages'] = []
    st.session_state['chat_session_id'] = str(uuid.uuid4())
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("📜 History")

# Load past sessions
if st.session_state['token']:
    try:
        headers = {"Authorization": f"Bearer {st.session_state['token']}"}
        resp = requests.get(f"{AGENT_BACKEND_URL}/sessions", headers=headers)
        if resp.status_code == 200:
            sessions = resp.json().get("sessions", [])
            
            # --- Empty State Message ---
            if not sessions:
                st.sidebar.info("No history.")
            
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
                    if st.button("🗑️", key=f"del_{session_id}", help="Delete Conversation"):
                        # Delete session
                        del_headers = {"Authorization": f"Bearer {st.session_state['token']}"}
                        try:
                            requests.delete(f"{AGENT_BACKEND_URL}/history/{session_id}", headers=del_headers)
                            
                            # If we deleted the active session, reset view
                            if st.session_state.get('chat_session_id') == session_id:
                                st.session_state['messages'] = []
                                st.session_state['chat_session_id'] = str(uuid.uuid4())
                            
                            st.toast("Conversation deleted successfully! 🗑️")
                            time.sleep(2) # Give time for toast to show
                            st.rerun()
                        except Exception as e:
                            st.sidebar.error(f"Error deleting: {e}")
    except Exception as e:
        st.sidebar.error(f"Connection error: {e}")

st.title("🤖 IT Support Chat")
st.markdown("""
Describe your technical problem and the agent will help you using the knowledge base and web search.
""")

# Display chat history
for message in st.session_state['messages']:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        # If assistant has a trace, show it in an expander
        if message["role"] == "assistant" and message.get("trace"):
            with st.expander("🔍 View thinking process"):
                m_code = render_mermaid(message["trace"])
                # Use a unique ID based on role and trace length/index
                u_id = f"hist_{str(hash(str(message['content'])))[-6:]}"
                st_mermaid(m_code, u_id)
                # Show steps breakdown
                st.markdown("### Steps Executed: ")
                for i, step in enumerate(message["trace"]):
                    node_icon = "🧠" if step["node"] == "agent" else "🛠️"
                    st.write(f"{i+1}. {node_icon} {step['description']}")

# Chat input
if prompt := st.chat_input("What can I help you today?"):
    # Add user message to state
    st.session_state['messages'].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get response from agent
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                headers = {"Authorization": f"Bearer {st.session_state['token']}"}
                response = requests.post(
                    f"{AGENT_BACKEND_URL}/chat/", # Added slash just in case
                    json={
                        "message": prompt, 
                        "session_id": st.session_state['chat_session_id']
                    },
                    headers=headers
                )
                
                if response.status_code == 200:
                    resp_json = response.json()
                    agent_response = resp_json.get("response")
                    trace = resp_json.get("trace", [])
                    
                    st.markdown(agent_response)
                    
                    # Show trace for the current response immediately
                    if trace:
                        with st.expander("🔍 View thinking process", expanded=False):
                            m_code = render_mermaid(trace)
                            st_mermaid(m_code, f"curr_{int(time.time())}")
                            st.markdown("### Steps executed:")
                            for i, step in enumerate(trace):
                                node_icon = "🧠" if step["node"] == "agent" else "🛠️"
                                st.write(f"{i+1}. {node_icon} {step['description']}")

                    st.session_state['messages'].append({
                        "role": "assistant", 
                        "content": agent_response,
                        "trace": trace
                    })
                    # Force rerun to update sidebar with new title if it was a new session
                    st.rerun()
                else:
                    st.error(f"Error ({response.status_code}): {response.text}")
            except Exception as e:
                st.error(f"Unexpected error: {str(e)}")
