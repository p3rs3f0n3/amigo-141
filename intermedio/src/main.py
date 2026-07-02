"""
A.M.I.G.O. — main.py
======================
API principal del backend con FastAPI.
Orquesta: datos_service + prompt_builder + API de Claude (Anthropic).

Endpoints:
  POST /chat          → conversación principal con el niño
  GET  /perfil/{mun}  → perfil regional de un municipio
  GET  /health        → healthcheck

Variables de entorno (.env):
  ANTHROPIC_API_KEY   → clave de la API de Claude
  AMIGO_MUNICIPIO_DEFAULT → municipio por defecto si no se detecta (ej: CALI)

Instalación:
  pip install fastapi uvicorn httpx pandas scikit-learn anthropic python-dotenv

Ejecución:
  uvicorn main:app --reload --port 8000
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from datos_service import DatosService
from prompt_builder import (
    construir_system_prompt,
    construir_user_prompt,
    construir_mensaje_riesgo,
    detectar_riesgo,
    detectar_frustracion,
    mensaje_motivacion,
)

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("amigo.api")

ANTHROPIC_API_KEY      = os.getenv("ANTHROPIC_API_KEY", "")
MUNICIPIO_DEFAULT      = os.getenv("AMIGO_MUNICIPIO_DEFAULT", "CALI")
MODELO_CLAUDE          = "claude-sonnet-4-6"
MAX_TOKENS_DEFAULT     = 600
MAX_HISTORIAL_TURNOS   = 10   # máximo de turnos que se mantienen en contexto

# ─────────────────────────────────────────────
# INICIO / CIERRE DE LA APP
# ─────────────────────────────────────────────
datos_svc = DatosService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Carga datasets al iniciar el servidor."""
    logger.info("🚀 Iniciando A.M.I.G.O. backend ...")
    await datos_svc.cargar_datasets()
    logger.info("✅ Backend listo")
    yield
    logger.info("🛑 Backend detenido")


app = FastAPI(
    title="A.M.I.G.O. API",
    description="Asistente Multimodal Inteligente para Guía y Orientación infantil — Backend",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # En producción: reemplazar con el dominio del frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# MODELOS PYDANTIC
# ─────────────────────────────────────────────
class Mensaje(BaseModel):
    rol:       str    # "user" | "assistant"
    contenido: str


class ChatRequest(BaseModel):
    mensaje:    str   = Field(..., min_length=1, max_length=1000,
                              description="Mensaje del niño")
    edad:       Optional[int]  = Field(None, ge=7, le=12,
                              description="Edad del estudiante (7-12)")
    municipio:  Optional[str]  = Field(None,
                              description="Municipio del estudiante (ej: CALI)")
    historial:  list[Mensaje]  = Field(default_factory=list,
                              description="Turnos anteriores de la conversación")


class ChatResponse(BaseModel):
    respuesta:      str
    tipo:           str   = "chat"           # "chat" | "alerta_bienestar"
    nivel_alerta:   str   = "ninguno"        # "ninguno" | "emocion" | "medio" | "alto"
    escalar:        bool  = False
    temas_detectados: list[str] = []
    municipio_usado:  str  = ""
    fuente_datos:     str  = ""


class PerfilResponse(BaseModel):
    municipio:          str
    nivel_matematicas:  str
    nivel_lectura:      str
    area_mas_debil:     str
    tasa_desercion:     Optional[float]
    tasa_aprobacion:    Optional[float]
    fuente:             str


# ─────────────────────────────────────────────
# LLAMADA A LA API DE CLAUDE
# ─────────────────────────────────────────────
async def llamar_claude(
    system_prompt: str,
    historial: list[dict],
    max_tokens: int = MAX_TOKENS_DEFAULT,
) -> str:
    """Envía la conversación a la API de Claude y retorna la respuesta en texto."""
    if not ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="ANTHROPIC_API_KEY no configurada. Agrega la clave en el archivo .env"
        )

    headers = {
        "x-api-key":         ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type":      "application/json",
    }
    payload = {
        "model":      MODELO_CLAUDE,
        "max_tokens": max_tokens,
        "system":     system_prompt,
        "messages":   historial,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            "https://api.anthropic.com/v1/messages",
            json=payload,
            headers=headers,
        )
        if r.status_code != 200:
            logger.error(f"Error Claude API: {r.status_code} — {r.text[:300]}")
            raise HTTPException(status_code=502, detail=f"Error al consultar la IA: {r.status_code}")

        data = r.json()
        return data["content"][0]["text"]


# ─────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────
@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Endpoint principal de conversación.
    Recibe el mensaje del niño y retorna la respuesta de A.M.I.G.O.
    """
    municipio = (req.municipio or MUNICIPIO_DEFAULT).upper().strip()

    # ── 1. Detección de riesgo (PRIMERO, siempre) ────────────────
    alerta = detectar_riesgo(req.mensaje)
    if alerta.nivel in ("alto", "medio"):
        logger.warning(f"🚨 Alerta {alerta.nivel} detectada | municipio: {municipio} | palabras: {alerta.detectado}")
        msg_riesgo = construir_mensaje_riesgo(alerta)
        return ChatResponse(
            respuesta=msg_riesgo["respuesta"],
            tipo="alerta_bienestar",
            nivel_alerta=alerta.nivel,
            escalar=alerta.escalar,
            municipio_usado=municipio,
        )

    # ── 2. Obtener perfil regional ────────────────────────────────
    perfil = await datos_svc.obtener_perfil_regional(municipio)

    # ── 3. Recuperador RAG — detectar tema de la pregunta ─────────
    contexto_rag = datos_svc.buscar_contexto(req.mensaje, municipio=municipio, k=5)
    nombres_temas = [r["fuente"] + ":" + r["documento"][:60] for r in contexto_rag]
    logger.info(f"📚 Temas detectados: {nombres_temas} | municipio: {municipio}")

    # ── 4. Manejar frustración ────────────────────────────────────
    frustrado = detectar_frustracion(req.mensaje)

    # ── 5. Construir system prompt ────────────────────────────────
    system = construir_system_prompt(
        edad=req.edad,
        perfil_regional=perfil,
        temas_rag=contexto_rag if contexto_rag else None,
    )
    if frustrado:
        motivacion = mensaje_motivacion(req.edad)
        system += f"\n\nIMPORTANTE: El niño parece frustrado. Comienza tu respuesta con este mensaje de aliento antes de explicar: '{motivacion}'"

    # ── 6. Armar historial para Claude ───────────────────────────
    # Limitar turnos para no exceder el contexto
    historial_reciente = req.historial[-(MAX_HISTORIAL_TURNOS * 2):]
    historial_claude = [
        {"role": m.rol, "content": m.contenido}
        for m in historial_reciente
    ]
    # Agregar el mensaje actual
    user_content = construir_user_prompt(req.mensaje, alerta if alerta.nivel == "emocion" else None)
    historial_claude.append({"role": "user", "content": user_content})

    # ── 7. Llamar a Claude ────────────────────────────────────────
    respuesta_ia = await llamar_claude(system, historial_claude)

    # ── 8. Si hay alerta de emoción, anteponer mensaje de apoyo ──
    if alerta.nivel == "emocion":
        respuesta_ia = f"{alerta.mensaje_apoyo}\n\n{respuesta_ia}"

    return ChatResponse(
        respuesta=respuesta_ia,
        tipo="chat",
        nivel_alerta=alerta.nivel,
        escalar=False,
        temas_detectados=nombres_temas,
        municipio_usado=municipio,
        fuente_datos=perfil.get("fuente", ""),
    )


@app.get("/perfil/{municipio}", response_model=PerfilResponse)
async def perfil_regional(municipio: str):
    """
    Devuelve el perfil regional de un municipio.
    Útil para que el frontend muestre el contexto educativo al cargar la app.
    """
    perfil = await datos_svc.obtener_perfil_regional(municipio)
    return PerfilResponse(
        municipio=perfil.get("municipio", municipio.upper()),
        nivel_matematicas=perfil.get("nivel_matematicas", "desconocido"),
        nivel_lectura=perfil.get("nivel_lectura", "desconocido"),
        area_mas_debil=perfil.get("area_mas_debil", "general"),
        tasa_desercion=perfil.get("tasa_desercion"),
        tasa_aprobacion=perfil.get("tasa_aprobacion"),
        fuente=perfil.get("fuente", ""),
    )


@app.get("/health")
async def health():
    """Healthcheck del servicio."""
    return {
        "status":          "ok",
        "datasets_cargados": datos_svc._cargado,
        "municipios_en_cache": list(datos_svc._cache_perfiles.keys()),
        "modelo_ia":       MODELO_CLAUDE,
        "api_key_configurada": bool(ANTHROPIC_API_KEY),
    }
