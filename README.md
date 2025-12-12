# Sistema de Soporte Técnico Potenciado por GenAI

Este repositorio alberga una solución integral para la gestión y resolución automatizada de tickets de soporte técnico. El proyecto combina una API robusta para la gestión de datos con un agente autónomo inteligente capaz de proponer soluciones.

## Estructura del Proyecto

El sistema está dividido en dos componente principales:

### 1. API de Gestión de Tickets (`api/`)
El núcleo del sistema de gestión. Provee las funcionalidades base para el equipo de soporte:
*   **Base de Conocimiento RAG**: Ingesta y vectorización de tickets históricos.
*   **Búsqueda Semántica**: Encuentra problemas similares ocurridos en el pasado.
*   **Asistente de Enriquecimiento**: Utiliza LLMs para resumir incidencias y sugerir expertos internos.

👉 **[Ver documentación e instalación del API](api/README.md)**

### 2. Agente de Resolución Autónoma (`agent_app/`)
Un agente inteligente diseñado para actuar sobre los tickets. Construido con LangGraph y Streamlit:
*   **Investigación**: Consulta la API principal para obtener contexto histórico.
*   **Búsqueda Web**: Utiliza herramientas de búsqueda (Tavily) para encontrar documentación pública y soluciones externas.
*   **Síntesis**: Genera una propuesta de solución paso a paso lista para el usuario.

👉 **[Ver documentación e instalación del Agente](agent_app/README.md)**

## Flujo de Trabajo Recomendado

1.  **Levantar el API (Parte 1)**: Es necesario que la API esté corriendo en el puerto 8000 para proveer contexto histórico.
2.  **Iniciar el Agente (Parte 2)**: Levantar el backend del agente y su interfaz gráfica para comenzar a resolver tickets.

Para detalles técnicos específicos, dependencias y configuración de variables de entorno, por favor consulta el `README.md` respectivo de cada módulo.
