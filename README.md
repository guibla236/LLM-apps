# 📰 Resumidor de Noticias - API FastAPI

Una API para resumir noticias automáticamente usando inteligencia artificial. Powered by **Groq AI** y construida con **FastAPI**.

## ✨ Características

- 🤖 **Resumen automático de noticias** usando modelos de IA (Groq)
- 📌 **Extracción de puntos clave** desde el contenido de la noticia
- 🎨 **Interfaz web amigable** con formularios intuitivos
- ⚡ **API REST rápida y confiable** con FastAPI
- 🔄 **CORS habilitado** para integraciones frontend
- 📊 **Validación robusta** de datos con Pydantic
- 🛡️ **Manejo de errores** con mensajes descriptivos
- 🔍 **Debugging detallado** en consola del servidor

## 🏗️ Estructura del Proyecto

```
Tarea_2/
├── api/
│   ├── main.py                          # Punto de entrada (ejecutable)
│   ├── app.py                           # Configuración de FastAPI
│   ├── requirements.txt                 # Dependencias Python
│   ├── .env                             # Variables de entorno (no versionado)
│   ├── .gitignore                       # Archivos ignorados por Git
│   │
│   ├── modules/                         # Módulos independientes
│   │   ├── __init__.py
│   │   └── news_summarizer.py          # Lógica de resumen con Groq
│   │
│   ├── templates/                       # Templates HTML
│   │   └── index.html                  # Página principal
│   │
│   ├── static/                          # Archivos estáticos
│   │   ├── css/
│   │   │   └── style.css               # Estilos CSS
│   │   └── js/
│   │       └── script.js               # Lógica del frontend
│   │
│   ├── tarea2/                          # Entorno virtual Python
│   │
│   └── .vscode/                         # Configuración VS Code
│       └── launch.json                  # Configuración del debugger
│
└── README.md                            # Este archivo
```

## 🚀 Quick Start

### 1. **Clonar/Descargar el Proyecto**

```bash
cd Tarea_2/api
```

### 2. **Crear y Activar Entorno Virtual**

```bash
python3 -m venv tarea2
source tarea2/bin/activate  # En Linux/Mac
# o
tarea2\Scripts\activate  # En Windows
```

### 3. **Instalar Dependencias**

```bash
pip install -r requirements.txt
```

### 4. **Configurar Variables de Entorno**

Crea un archivo `.env` en la carpeta `api/`:

```env
GROQ_API_KEY=tu_clave_api_de_groq_aqui
```

> 📌 Obtén tu clave API gratis en [console.groq.com](https://console.groq.com)

### 5. **Ejecutar la Aplicación**

```bash
python main.py
```

La API estará disponible en: **http://localhost:8000**

## 📡 Endpoints

### `GET /`
**Descripción**: Devuelve la página principal HTML

**Ejemplo**:
```bash
curl http://localhost:8000/
```

---

### `POST /api/summarize_news`
**Descripción**: Genera un resumen y puntos clave de una noticia

**Parámetros (JSON)**:
```json
{
  "title": "Título de la noticia",
  "content": "Contenido completo de la noticia aquí..."
}
```

**Ejemplo de solicitud**:
```bash
curl -X POST http://localhost:8000/api/summarize_news \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Pronóstico del tiempo para el fin de semana",
    "content": "Los meteorólogos predicen un aumento en las temperaturas hacia el fin de semana, con máximas de hasta 35°C el sábado..."
  }'
```

**Respuesta exitosa (200)**:
```json
{
  "original_title": "Pronóstico del tiempo para el fin de semana",
  "summary": "Se espera un ascenso en las temperaturas hacia el fin de semana, con máximas de hasta 35°C el sábado, seguidas de lluvias el domingo con temperaturas máximas de 24°C.",
  "summary_length": 145,
  "key_points": [
    "Temperaturas máximas de hasta 35°C el sábado",
    "Lluvias previstas para el domingo con máxima de 24°C",
    "Posibles chaparrones en la noche del jueves, viernes y sábado"
  ]
}
```

**Respuesta de error (500)**:
```json
{
  "detail": "Error al generar el resumen: [razón del error]"
}
```

## 🔧 Configuración del Debugger (VS Code)

El proyecto está preconfigurado para usar el debugger de VS Code:

1. Abre la carpeta `Tarea_2` en VS Code
2. Ve a la pestaña "Run and Debug" (Ctrl+Shift+D)
3. Selecciona "Depurador de Python: FastAPI"
4. Presiona F5 o el botón de play

El debugger ejecutará `main.py` desde la carpeta `api/` automáticamente.

## 📚 Tecnologías Utilizadas

| Tecnología | Versión | Propósito |
|-----------|---------|----------|
| FastAPI | 0.124.1 | Framework web asincrónico |
| Uvicorn | 0.24.0 | Servidor ASGI |
| Pydantic | - | Validación de datos |
| Groq | 0.9.0 | API de IA para resumen |
| Python-dotenv | 1.0.0 | Gestión de variables de entorno |
| HTTPX | 0.27.0 | Cliente HTTP asincrónico |

## 🏭 Arquitectura

### Flujo de Datos

```
┌─────────────────────┐
│  Frontend (HTML/JS) │
└──────────┬──────────┘
           │ POST /api/summarize_news
           │ { title, content }
           ▼
┌─────────────────────┐
│  FastAPI Endpoint   │ (app.py)
│ summarize_news_..   │
└──────────┬──────────┘
           │ Llama función
           ▼
┌─────────────────────┐
│  Módulo Independ.   │ (modules/news_summarizer.py)
│  summarize_news()   │
└──────────┬──────────┘
           │ Valida datos
           │ Llama API Groq
           ▼
┌─────────────────────┐
│  Groq AI API        │ (qwen/qwen3-32b)
│  (Cloud)            │
└──────────┬──────────┘
           │ Retorna JSON
           ▼
┌─────────────────────┐
│  Parsea respuesta   │
│  Extrae puntos clave│
└──────────┬──────────┘
           │ NewsSummary
           ▼
┌─────────────────────┐
│  Frontend (JSON)    │
│  Muestra resultado  │
└─────────────────────┘
```

## 🔐 Validación y Manejo de Errores

### Validación de Entrada
- **Campos requeridos**: `title` y `content` no pueden estar vacíos
- **Limpieza de datos**: Comillas duplicadas y espacios se normalizan automáticamente
- **Modelos Pydantic**: Validación fuerte de tipos y estructura

### Manejo de Errores
- **Errores de validación (422)**: Datos inválidos o incompletos
- **Errores del servidor (500)**: Fallos en API Groq o procesamiento
- **Logging**: Todos los errores se registran en `stderr` del servidor
- **Mensajes amigables**: El frontend recibe mensajes claros sobre qué falló

## 📝 Variables de Entorno

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `GROQ_API_KEY` | Sí | Clave de API de Groq |

## 🧪 Debugging

### Logs en el Servidor

Todos los eventos importantes se registran en `stderr`:

```
========== DEBUG: Llamada a /api/summarize_news ==========
DEBUG: Datos recibidos: NewsInput(title='...', content='...')
DEBUG: Llamando a summarize_news...
DEBUG: Respuesta bruta de Groq: {...}
DEBUG: Parseado exitosamente
========== DEBUG: Endpoint finalizado exitosamente ==========
```

### Puntos de Quiebre

Puedes establecer puntos de quiebre en:
- `app.py` - Endpoint `summarize_news_endpoint()`
- `modules/news_summarizer.py` - Función `summarize_news()`

## 🤝 Contribuciones

Para mejorar el proyecto:

1. Crea una rama: `git checkout -b feature/mi-mejora`
2. Haz commits: `git commit -am 'Agrega mi mejora'`
3. Push: `git push origin feature/mi-mejora`
4. Abre un Pull Request

## 📄 Licencia

Este proyecto es parte del Bootcamp GenAI E2.

## 👤 Autor

Guillermo - GenAI E2 Bootcamp

## 📞 Soporte

Si encuentras problemas:

1. Verifica que `GROQ_API_KEY` esté configurada en `.env`
2. Asegúrate de que el entorno virtual esté activado
3. Revisa los logs en la consola del servidor
4. Comprueba la conectividad a internet (se necesita para Groq API)

---

**¡Gracias por usar el Resumidor de Noticias! 🎉**
