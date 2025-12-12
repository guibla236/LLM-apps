# Sistema de Gestión de Tickets de Soporte

Este repositorio contiene un sistema inteligente para la gestión, búsqueda y mejora de tickets de soporte técnico utilizando técnicas de RAG (Retrieval-Augmented Generation) y modelos de lenguaje (LLMs).

## Descripción del Proyecto

El objetivo principal de esta aplicación es optimizar el flujo de trabajo de los equipos de soporte mediante:

*   **Ingesta de Tickets**: Carga de tickets individuales o masiva mediante archivos JSON.
*   **Búsqueda Semántica**: Recuperación de tickets similares basada en vectores (Pinecone) para encontrar soluciones previas a problemas recurrentes.
*   **Asistente IA**: Enriquecimiento de la información de los tickets, generando resúmenes automáticos y sugiriendo contactos relevantes dentro de la organización.

## Estructura

El núcleo de la aplicación se encuentra en la carpeta `api/`, que contiene:
*   Una API REST construida con **FastAPI**.
*   Una interfaz de usuario web ligera.
*   Módulos para la ingesta, vectorización (embeddings) y recuperación de datos.

## Comienza Aquí

Toda la documentación técnica, los requisitos de instalación y los pasos para ejecutar la aplicación se encuentran detallados en el directorio de la API.

� **[Ver instrucciones de instalación y uso en api/README.md](api/README.md)**
