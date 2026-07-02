# A.M.I.G.O. — Backend

**Asistente Multimodal Inteligente para Guía y Orientación infantil**  
Concurso Datos al Ecosistema 2026 — IA para Colombia (MinTIC)

---

## ¿Qué es este backend?

Es el cerebro de A.M.I.G.O. Recibe el mensaje de un niño o niña de 7 a 12 años, consulta datos educativos reales de `datos.gov.co`, construye un contexto inteligente y le pide a Claude (Anthropic) que responda de forma adaptada a la edad y al territorio del estudiante.

Si el niño escribe algo que sugiere que está en riesgo, el sistema **no llama a la IA** — responde directamente con un mensaje de apoyo y escala la alerta.

---

## Estructura de archivos

```
amigo-backend/
├── main.py              # API FastAPI — punto de entrada, endpoints
├── datos_service.py     # Carga, limpieza, biblioteca RAG y perfiles regionales
├── prompt_builder.py    # Construcción de prompts, detector de riesgo, configs por edad
├── requirements.txt     # Dependencias Python
├── .env                 # Variables de entorno (NO subir a Git)
└── .env.example         # Plantilla del .env
```

---

## Cómo instalar y correr

```bash
# 1. Crear entorno virtual
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
cp .env.example .env
# Editar .env y poner tu ANTHROPIC_API_KEY

# 4. Correr el servidor
uvicorn main:app --reload --port 8000
```

El servidor queda disponible en `http://localhost:8000`.  
La documentación automática de la API en `http://localhost:8000/docs`.

---

## Variables de entorno (.env)

| Variable | Descripción | Ejemplo |
|---|---|---|
| `ANTHROPIC_API_KEY` | Clave de la API de Claude (Anthropic) | `sk-ant-...` |
| `AMIGO_MUNICIPIO_DEFAULT` | Municipio por defecto si el frontend no envía uno | `CALI` |

---

## Endpoints disponibles

### `POST /chat`
Endpoint principal. Recibe el mensaje del niño y retorna la respuesta de A.M.I.G.O.

**Body (JSON):**
```json
{
  "mensaje": "no entiendo cómo se hacen las fracciones",
  "edad": 10,
  "municipio": "CALI",
  "historial": [
    { "rol": "user",      "contenido": "hola" },
    { "rol": "assistant", "contenido": "¡Hola! ¿En qué te puedo ayudar hoy?" }
  ]
}
```

**Respuesta (JSON):**
```json
{
  "respuesta": "¡Hola! Las fracciones son más fáciles de lo que parecen...",
  "tipo": "chat",
  "nivel_alerta": "ninguno",
  "escalar": false,
  "temas_detectados": ["saber:Municipio: CALI | Grado: 5 | Puntaje matemáticas: 312"],
  "municipio_usado": "CALI",
  "fuente_datos": "datos_abiertos"
}
```

**Tipos de respuesta posibles:**

| `tipo` | `nivel_alerta` | Qué pasó |
|---|---|---|
| `chat` | `ninguno` | Conversación normal |
| `chat` | `emocion` | El niño expresó tristeza — la IA responde con empatía primero |
| `alerta_bienestar` | `medio` | Se detectó bullying o maltrato — respuesta de apoyo directo, sin IA |
| `alerta_bienestar` | `alto` | Riesgo inmediato — respuesta de apoyo + Línea 106, sin IA |

---

### `GET /perfil/{municipio}`
Devuelve el perfil educativo regional de un municipio, construido con datos reales de `datos.gov.co`.

**Ejemplo:** `GET /perfil/CALI`

```json
{
  "municipio": "CALI",
  "nivel_matematicas": "medio",
  "nivel_lectura": "medio",
  "area_mas_debil": "matematicas",
  "tasa_desercion": 3.2,
  "tasa_aprobacion": 88.5,
  "fuente": "datos_abiertos"
}
```

---

### `GET /health`
Healthcheck del servicio. Indica si los datasets están cargados y si la API key está configurada.

```json
{
  "status": "ok",
  "datasets_cargados": true,
  "municipios_en_cache": ["CALI", "BOGOTA"],
  "modelo_ia": "claude-sonnet-4-6",
  "api_key_configurada": true
}
```

---

## Flujo completo de una conversación

```
Niño escribe un mensaje
        │
        ▼
┌─────────────────────────────┐
│  1. Detector de riesgo      │  ← prompt_builder.py
│     (SIEMPRE va primero)    │
└────────────┬────────────────┘
             │
    ┌────────┴────────┐
    │ ¿Hay riesgo?    │
    └────────┬────────┘
          SI │ nivel medio/alto          NO │
             ▼                              ▼
   Respuesta de apoyo         ┌─────────────────────────────┐
   directo + escalar=true     │  2. Perfil regional          │ ← datos_service.py
   (sin llamar a la IA)       │     datos.gov.co por municipio│
                              └────────────┬────────────────┘
                                           ▼
                              ┌─────────────────────────────┐
                              │  3. Búsqueda RAG             │ ← datos_service.py
                              │     registros relevantes      │
                              │     del dataset real          │
                              └────────────┬────────────────┘
                                           ▼
                              ┌─────────────────────────────┐
                              │  4. Construir system prompt  │ ← prompt_builder.py
                              │     edad + perfil + RAG      │
                              └────────────┬────────────────┘
                                           ▼
                              ┌─────────────────────────────┐
                              │  5. Llamar a Claude API      │ ← main.py
                              │     con historial completo   │
                              └────────────┬────────────────┘
                                           ▼
                                   Respuesta adaptada
                                   al niño y su territorio
```

---

## Cómo funciona cada archivo

### `datos_service.py`

Es el módulo de datos. Hace cuatro cosas en orden:

**1. Descarga** los datasets de `datos.gov.co` al iniciar el servidor (una sola vez):
- Pruebas Saber 3°, 5° y 9° (`4h84-62xp`) — el más relevante para niños de 7-12 años
- MEN estadísticas por municipio (`nudc-7mev`) — cobertura, deserción, aprobación

**2. Limpia** cada dataset con `limpiar_dataset()`:
- Estandariza nombres de columnas (minúsculas, sin espacios)
- Reemplaza celdas vacías, `"nan"`, `"-"`, `"n/a"` por valor nulo real
- Elimina columnas que son 100% vacías
- Elimina filas completamente vacías
- Elimina duplicados exactos
- Registra en log cuántas filas/columnas se eliminaron

**3. Construye la biblioteca de documentos** con `construir_biblioteca()`:  
Convierte cada fila del dataset en un texto consultable. Por ejemplo, una fila de Saber 3°5°9° se convierte en:
```
Municipio: CALI | Departamento: VALLE DEL CAUCA | Grado: 5 |
Puntaje matemáticas: 312 | Puntaje lenguaje: 298 | Zona: Urbana
```
Este es el mismo patrón del notebook de capacitación del concurso.

**4. Construye el recuperador RAG** con `RecuperadorRAG`:  
Vectoriza todos los documentos con TF-IDF y queda listo para buscar por similitud coseno. Cuando el niño hace una pregunta, el sistema encuentra los registros reales de `datos.gov.co` más relevantes y se los pasa a Claude como contexto.

El método `obtener_perfil_regional(municipio)` calcula:
- Nivel de matemáticas y lectura (alto / medio / bajo / muy bajo)
- Área más débil del municipio
- Tasa de deserción y aprobación

Y lo cachea en memoria para no recalcular en cada mensaje.

---

### `prompt_builder.py`

Construye lo que se le dice a Claude y detecta señales de alerta.

**Configs por edad** — hay una configuración distinta para cada año de 7 a 12:

| Edad | Tono | Instrucción |
|---|---|---|
| 7 | Muy cercano y simple | Frases cortas, emojis, ejemplos con frutas y animales |
| 8 | Cercano y simple | Una pregunta al final para verificar comprensión |
| 9 | Amigable | Paso a paso + ejemplo resuelto + uno para intentar |
| 10 | Amigable y motivador | Ejemplo resuelto + ejercicio corto |
| 11 | Motivador | Vocabulario un poco más técnico + 1-2 ejercicios |
| 12 | Tutor académico | Precisión + procedimiento + práctica |

**Detector de riesgo** en tres niveles:

| Nivel | Ejemplos de frases detectadas | Acción |
|---|---|---|
| `alto` | "me quiero morir", "no quiero vivir" | Respuesta de apoyo + Línea 106, `escalar=true` |
| `medio` | "me pegan", "me hacen bullying", "tengo mucho miedo" | Mensaje de apoyo + orientación, `escalar=true` |
| `emocion` | "estoy triste", "tengo miedo", "estoy nervioso" | La IA responde con empatía primero |

**Reglas del agente** que siempre se le envían a Claude:
- Nunca hacer la tarea por el niño — guiar con preguntas
- Lenguaje cálido, paciente y motivador
- Ejemplos con cosas de Colombia (arepa, aguacate, chiva, fútbol)
- Siempre terminar con una pregunta o reto corto

---

### `main.py`

Es el punto de entrada. Orquesta los otros dos módulos y expone la API con FastAPI.

Al iniciar el servidor (`lifespan`) llama a `datos_svc.cargar_datasets()` automáticamente — los datos quedan en memoria para toda la vida del proceso.

En cada petición `POST /chat` el flujo es:
1. Detectar riesgo → si es alto o medio, responder sin IA
2. Obtener perfil regional del municipio (con caché)
3. Buscar contexto RAG en los datasets reales
4. Detectar frustración y agregar motivación si aplica
5. Construir el system prompt con toda la información
6. Llamar a Claude con el historial completo
7. Si hay alerta de emoción, anteponer el mensaje de empatía

El historial se limita a los últimos 10 turnos para no exceder el contexto de la API.

---

## Datasets utilizados (datos.gov.co)

| Dataset | ID | Uso |
|---|---|---|
| Resultados Pruebas Saber 3°, 5° y 9° | `4h84-62xp` | Desempeño académico de primaria — PRINCIPAL |
| MEN estadísticas por municipio | `nudc-7mev` | Cobertura, deserción, aprobación |
| MEN estadísticas por departamento | `ji8i-4anb` | Respaldo si faltan datos municipales |
| DIVIPOLA geolocalizados | `vafm-j2df` | Coordenadas para el mapa (Leaflet.js) |

Todos se consumen vía API Socrata (SODA):  
`https://www.datos.gov.co/resource/{ID}.csv?$limit=5000`

---

## Dependencias principales

| Librería | Para qué se usa |
|---|---|
| `fastapi` | Framework de la API REST |
| `uvicorn` | Servidor ASGI |
| `httpx` | Peticiones HTTP asíncronas a datos.gov.co y Claude API |
| `pandas` | Carga, limpieza y análisis de datasets |
| `scikit-learn` | Vectorización TF-IDF y similitud coseno (RAG) |
| `numpy` | Operaciones matriciales del recuperador |
| `anthropic` | SDK de Claude (también usamos httpx directo) |
| `python-dotenv` | Lectura del archivo `.env` |

---

## Consideraciones de producción

- **API keys**: nunca subir el `.env` al repositorio. Está en `.gitignore`.
- **CORS**: en `main.py` está configurado como `allow_origins=["*"]`. En producción reemplazar con el dominio del frontend.
- **Rate limiting**: los datasets se descargan una sola vez al iniciar. Los perfiles regionales se cachean en memoria. No se llama a `datos.gov.co` en cada mensaje del chat.
- **Fallback**: si `datos.gov.co` está caído al iniciar, el sistema usa perfiles de respaldo para las ciudades principales (Cali, Bogotá, Medellín) y un perfil genérico para el resto.
- **Módulo de bienestar**: las alertas de riesgo medio y alto se loguean con `logger.warning`. En la siguiente fase se conectarán a blockchain (Ethereum/Sepolia) para registro inmutable.
