# Marco Metodológico — CRISP-ML

## A.M.I.G.O. — Equipo 141

La metodología utilizada es **CRISP-ML (Cross-Industry Standard Process for Machine Learning)**, adaptada al contexto de datos abiertos colombianos y al desarrollo de un asistente conversacional educativo.

---

## Fase 1 — Comprensión del negocio y los datos

**Objetivo de negocio:** Crear un asistente educativo que acompañe a niños de 7-12 años en zonas vulnerables de Colombia, personalizando el aprendizaje según el contexto territorial.

**Objetivo de ML:** Construir un sistema RAG (Retrieval-Augmented Generation) que recupere registros educativos reales por municipio y los use como contexto para generar respuestas adaptadas por edad mediante un LLM.

**Criterio de éxito:**
- Respuestas adaptadas correctamente a la edad del estudiante
- Uso efectivo del perfil regional en la personalización
- Detección correcta de señales de riesgo psicosocial
- Tiempo de respuesta < 5 segundos

---

## Fase 2 — Comprensión de los datos

**Fuentes identificadas:** 26 datasets de datos.gov.co (ver `docs/endpoints_AMIGO.txt`)

**Datasets principales:**

| Dataset | ID | Filas aprox. | Columnas |
|---|---|---|---|
| Saber 3°, 5° y 9° | `4h84-62xp` | Por confirmar | Por confirmar |
| MEN por municipio | `nudc-7mev` | 15.707 | 41 |
| MEN por departamento | `ji8i-4anb` | 462 | 37 |
| DIVIPOLA geolocalizados | `vafm-j2df` | 1.121 | 8 |

**Exploración inicial:** ver `notebooks/01_EDA_exploracion_datos.ipynb`

---

## Fase 3 — Preparación de los datos

**Proceso de limpieza implementado en `src/datos_service.py` → función `limpiar_dataset()`:**

1. Estandarización de nombres de columnas (minúsculas, sin espacios)
2. Reemplazo de valores nulos: `""`, `"nan"`, `"none"`, `"-"`, `"n/a"` → `NaN`
3. Eliminación de columnas 100% vacías
4. Eliminación de filas completamente vacías
5. Eliminación de duplicados exactos
6. Reporte de calidad: % celdas vacías, columnas disponibles

**Transformación principal — generación de documentos RAG:**

Cada fila del dataset se convierte en un texto consultable mediante `fila_a_documento()`:
```
Municipio: CALI | Departamento: VALLE DEL CAUCA | Grado: 5 |
Puntaje matemáticas: 312 | Puntaje lenguaje: 298 | Zona: Urbana
```

Ver detalle en `notebooks/02_limpieza_transformacion.ipynb`

---

## Fase 4 — Modelamiento

**Técnica principal: RAG ligero (Retrieval-Augmented Generation)**

Componentes:
- **Vectorización:** TF-IDF con n-gramas (1,2) sobre documentos normalizados
- **Recuperación:** similitud coseno entre pregunta del usuario y documentos del dataset
- **Generación:** Claude API (Anthropic) — modelo `claude-sonnet-4-6`

**Componente secundario: detección de riesgo NLP**

- Matching por palabras clave en tres niveles: alto, medio, emoción
- Sin modelo entrenado — basado en listas curadas de frases de riesgo
- Implementado en `src/prompt_builder.py` → función `detectar_riesgo()`

**Personalización por edad:**
- 6 configuraciones distintas (7 a 12 años)
- Adaptan tono, complejidad y longitud de respuesta

---

## Fase 5 — Evaluación

**Métricas de calidad del RAG:**
- Score de similitud coseno promedio de los documentos recuperados
- Cobertura de municipios en el dataset (% con al menos 1 registro)

**Métricas de calidad del sistema:**
- Precisión del detector de riesgo (validación manual con casos de prueba)
- Tiempo de respuesta end-to-end

Ver resultados en `notebooks/04_modelo_predictivo.ipynb` y `reports/reporte_final.pdf`

---

## Fase 6 — Despliegue

**Arquitectura de despliegue:**
- Backend: FastAPI + uvicorn (servidor ASGI)
- Datos: cargados en memoria RAM al iniciar, actualizados con reinicio del servidor
- Frontend: React (aplicación web responsive)
- API: endpoints REST documentados en `/docs`

**Consideraciones éticas:**
- Solo se almacenan agregados por municipio, nunca datos individuales de menores
- Las alertas de riesgo se loguean y escalan, no se procesan con IA
- API keys nunca en el repositorio (`.env` + `.gitignore`)
- Blockchain (Ethereum/Sepolia) para registro inmutable de alertas — fase 2

---

## Resumen del flujo CRISP-ML

```
Datos brutos           Limpieza              Documentos RAG
datos.gov.co    →   limpiar_dataset()   →   fila_a_documento()
                                                    │
                                             TF-IDF vectorizer
                                                    │
Pregunta niño   →   buscar_contexto()  →   Top-k documentos
                                                    │
                    construir_system_prompt()        │
                    (edad + perfil + RAG)  ←────────┘
                                                    │
                         Claude API         →   Respuesta adaptada
```
