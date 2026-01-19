# Limitaciones y Políticas de Uso de la API

Este documento detalla las medidas de seguridad y control de consumo implementadas para proteger la integridad y disponibilidad del sistema.

## 1. Control de Cuotas (Uso Diario)

El sistema utiliza un modelo de cuotas híbrido para evitar el abuso de recursos de IA (Groq/Pinecone).

### Cuota por Usuario
- **Límite:** 100 consultas por día.
- **Identificación:** Se vincula al `username` del usuario autenticado (vía JWT o API Key).
- **Reinicio:** Se resetea automáticamente cada día a las 00:00 UTC.

### Cuota por Dirección IP (Anti Multi-Cuenta)
- **Límite:** 200 consultas totales por día por IP.
- **Propósito:** Evitar que un usuario eluda su límite personal creando múltiples cuentas desde la misma conexión.
- **Comportamiento:** Si la IP alcanza el límite, todas las peticiones desde esa conexión serán rechazadas con un error `403 Forbidden`, incluso si la cuenta individual aún tiene crédito.

---

## 2. Rate Limiting (Protección contra DoS)

Implementado mediante `slowapi` para evitar picos de carga y ataques de fuerza bruta.

- **Ingesta de Tickets:** 10 peticiones por minuto.
- **Resumen de Noticias:** 5 peticiones por minuto.
- **Consultas RAG:** 10 peticiones por minuto.
- **Identificación:** Se aplica por dirección IP del cliente.

---

## 3. Seguridad en el Registro

Para prevenir la creación masiva de cuentas:
- **Límite de Registros por IP:** Máximo 3 cuentas nuevas por día desde la misma dirección IP.
- **Validación de Identidad:** Emails y nombres de usuario deben ser únicos (protegido por índices únicos en MongoDB).

---

## 4. Limitaciones de Payload

Para evitar ataques de denegación de servicio por agotamiento de memoria o procesamiento de LLM:
- **Títulos de Noticias:** Máximo 255 caracteres.
- **Contenido de Noticias:** Máximo 10,000 caracteres.
- **Descripción de Tickets:** Validado mediante modelos Pydantic para asegurar tipos y longitudes coherentes.

---

## 5. Respuestas de Error y Auditoría

- **Errores Técnicos:** En caso de fallos internos (500), la API devuelve un `error_id` único y oculta la traza técnica (traceback) al usuario final.
- **Auditoría y Monitoreo:** Los administradores tienen visibilidad total de estos límites a través del **Panel Administrativo**, pudiendo observar en tiempo real:
    - Consumo acumulado por dirección IP.
    - Historial de registros recientes por IP.
    - Detalle técnico completo de errores mediante el `error_id`.
