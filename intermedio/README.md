# 🤖 A.M.I.G.O.
### Asistente Multimodal Inteligente para Guía y Orientación infantil

**Concurso Datos al Ecosistema 2026 — IA para Colombia (MinTIC)**  
**Equipo ID:** 141 | **Nivel:** Intermedio | **Categoría:** Innovación Social / Innovación y Tecnología

---

## ¿Qué es A.M.I.G.O.?

A.M.I.G.O. es un asistente educativo con inteligencia artificial que acompaña a niños y niñas colombianas de **7 a 12 años** en su proceso de aprendizaje, adaptando sus respuestas según el contexto territorial y educativo a partir de **datos abiertos de datos.gov.co**.

El sistema no hace las tareas por el niño — las explica, guía paso a paso y hace preguntas para que el estudiante llegue a la respuesta por sus propios medios.

Adicionalmente, cuenta con un **módulo de bienestar** que detecta señales de riesgo psicosocial en el lenguaje del estudiante y activa rutas de apoyo cuando es necesario.

---

## El problema que resuelve

En Colombia, millones de niños en zonas rurales y urbanas vulnerables no tienen acceso a tutorías privadas ni acompañamiento académico en casa. Al mismo tiempo, existe información pública valiosa sobre el desempeño educativo por municipio que no se aprovecha para personalizar el aprendizaje.

**A.M.I.G.O. transforma esos datos abiertos en experiencias educativas personalizadas y accesibles para cualquier niño con conexión a internet.**

---

## Significado del nombre

| Letra | Valor |
|---|---|
| **A** | Acompañamiento — siempre presente, no deja solo al estudiante |
| **M** | Motivador — impulsa a seguir, saca lo mejor del niño |
| **I** | Inteligente — convierte lo complejo en algo sencillo |
| **G** | Guía — orienta con claridad sin hacer el trabajo por el estudiante |
| **O** | Objetivo — honesto y justo para que el niño realmente mejore |

---

## Arquitectura de la solución

```
Frontend (React)
      │
      ▼
Backend (FastAPI / Python)
  ├── datos_service.py   → descarga, limpia y vectoriza datos de datos.gov.co
  ├── prompt_builder.py  → adapta el prompt por edad y detecta riesgo
  └── main.py            → API REST + orquestación
      │
      ├──→ datos.gov.co (Saber 3°5°9°, MEN, DIVIPOLA)
      └──→ Claude API (Anthropic) — IA generativa
```

---

## Datos abiertos utilizados

| Dataset | ID | Uso |
|---|---|---|
| Resultados Pruebas Saber 3°, 5° y 9° | `4h84-62xp` | Desempeño académico de primaria — PRINCIPAL |
| MEN estadísticas por municipio | `nudc-7mev` | Cobertura, deserción, aprobación |
| MEN estadísticas por departamento | `ji8i-4anb` | Respaldo si faltan datos municipales |
| DIVIPOLA geolocalizados | `vafm-j2df` | Coordenadas para el mapa |
| Encuesta Convivencia y Seguridad (ECSC) | `qawu-zaae` | Módulo de bienestar |
| Directorio Único Establecimientos (DUE) | `28t6-6wvz` | Mapa de colegios |

Ver catálogo completo (26 fuentes) en [`docs/endpoints_AMIGO.txt`](docs/endpoints_AMIGO.txt)

---

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Frontend | React, Chart.js, Leaflet.js |
| Backend | Python, FastAPI, uvicorn |
| IA | Claude API (Anthropic), TF-IDF + coseno (RAG) |
| Datos | datos.gov.co — API Socrata (SODA) |
| Blockchain | Ethereum / Sepolia (registro de alertas) |
| Control de versiones | GitHub |

---

## Estructura del repositorio

```
amigo/
├── RECURSOS/              # Presentación del proyecto (.pptx, .pdf)
├── docs/                  # Documentación técnica completa
│   ├── architecture.md        # Arquitectura del backend
│   ├── data_dictionary.md     # Diccionario de variables
│   ├── planteamiento_problema.md
│   ├── marco_metodologico.md  # CRISP-ML
│   ├── fuentes_datos.md       # Datasets y evidencia de uso
│   ├── conclusiones.md
│   └── endpoints_AMIGO.txt    # Catálogo completo de endpoints
├── data/
│   ├── 01_raw/            # Datos originales de datos.gov.co
│   ├── 02_intermediate/   # Datos con limpieza inicial
│   ├── 03_primary/        # Datos transformados y consolidados
│   └── 04_model_output/   # Perfiles regionales generados
├── notebooks/             # Análisis exploratorio y limpieza
├── src/                   # Código fuente del backend
│   ├── main.py
│   ├── datos_service.py
│   └── prompt_builder.py
├── frontend/              # Aplicación React
├── models/                # Modelos entrenados
├── reports/               # Resultados y figuras
├── tests/                 # Pruebas unitarias
├── pipelines/             # Pipeline ML integrado
├── requirements.txt
└── .env.example
```

---

## Cómo correr el proyecto

```bash
# 1. Clonar el repositorio
git clone https://github.com/TU_USUARIO/amigo-141.git
cd amigo-141

# 2. Crear entorno virtual
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env y agregar ANTHROPIC_API_KEY

# 5. Correr el backend
uvicorn src.main:app --reload --port 8000
```

API disponible en `http://localhost:8000`  
Documentación interactiva en `http://localhost:8000/docs`

---

## Impacto esperado

- **Social:** democratizar el acceso a acompañamiento académico para niños sin recursos en zonas rurales y urbanas vulnerables de Colombia
- **Educativo:** refuerzo personalizado en el área más débil de cada municipio según datos reales del ICFES y el MEN
- **Protección infantil:** detección temprana de señales de riesgo psicosocial (bullying, maltrato, ideación) con activación de rutas de apoyo
- **Escalabilidad:** cualquier municipio del país con conexión a internet puede usar el sistema

---

## Equipo

Proyecto A.M.I.G.O. — Equipo 141  
Concurso Datos al Ecosistema 2026 — MinTIC / datos.gov.co

---

## Licencia

MIT License — ver archivo `LICENSE`
