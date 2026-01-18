import streamlit as st
import requests
import json

st.set_page_config(page_title="Agente de Resolución de Tickets", page_icon="🤖")

st.title("🤖 Agente de Resolución de Tickets")
st.markdown("""
Este agente inteligente te ayuda a resolver tickets de soporte.
1. Analiza el ticket.
2. Busca casos similares en la base de datos (RAG).
3. Investiga en internet documentación reciente.
4. Propone una solución completa.
""")

# Input for Ticket JSON
ticket_json_input = st.text_area(
    "Pega el JSON del Ticket aquí:",
    height=300,
    placeholder='''{
      "ticketId": "12345",
      "title": "Problema con la impresora",
      "priority": "HIGH",
      "owner": "Juan Pérez - IT",
      "description": "La impresora no responde y muestra un error de conexión.",
      "impact": "Alto",
      "actions": "Reinicié la impresora y verifiqué los cables."
    }'''
)

if st.button("Resolver Ticket"):
    if not ticket_json_input:
        st.error("Por favor, ingresa el JSON del ticket.")
    else:
        try:
            # Parse JSON to validate
            ticket_data = json.loads(ticket_json_input)
            
            with st.spinner("El agente está trabajando... esto puede tomar unos segundos..."):
                # Call Agent Backend
                response = requests.post(
                    "http://localhost:8001/solve_ticket",
                    json={"ticket": ticket_data}
                )
                
                if response.status_code == 200:
                    solution = response.json().get("solution", "No solution returned.")
                    st.success("¡Análisis completado!")
                    st.markdown("### 💡 Solución Propuesta")
                    st.markdown(solution)
                else:
                    st.error(f"Error del servidor: {response.text}")
                    
        except json.JSONDecodeError:
            st.error("El formato ingresado no es un JSON válido.")
        except Exception as e:
            st.error(f"Ocurrió un error: {str(e)}")
