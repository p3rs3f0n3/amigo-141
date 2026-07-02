"""
A.M.I.G.O. — prompt_builder.py
================================
Construye los prompts que se envían a la API de Claude (Anthropic)
adaptando el lenguaje, tono y contenido según:
  - Edad del niño (7-12 años)
  - Municipio / perfil regional
  - Tema detectado por el recuperador RAG
  - Historial de la conversación

También contiene el detector de señales de riesgo (bienestar).
"""

import re
from dataclasses import dataclass, field
from typing import Optional

# ─────────────────────────────────────────────
# CONFIGURACIÓN POR EDAD
# ─────────────────────────────────────────────
@dataclass
class ConfigEdad:
    rango:       str
    tono:        str
    complejidad: str
    max_tokens:  int
    instruccion: str


CONFIGS_EDAD = {
    7:  ConfigEdad("7 años",  "muy cercano y simple", "muy básico",  400,
                   "Usa palabras muy simples. Frases cortas. Un solo concepto a la vez. Emojis amigables. Ejemplos con cosas del día a día como frutas, juguetes o animales."),
    8:  ConfigEdad("8 años",  "cercano y simple",     "básico",      450,
                   "Usa palabras simples. Ejemplos concretos con objetos cotidianos. Haz una pregunta al final para verificar que entendió."),
    9:  ConfigEdad("9 años",  "amigable",             "básico-medio",500,
                   "Explica paso a paso. Usa comparaciones con situaciones de la vida real. Incluye un ejemplo resuelto y propón uno para que el niño intente."),
    10: ConfigEdad("10 años", "amigable y motivador", "medio",       550,
                   "Explica el concepto claramente. Muestra un ejemplo resuelto paso a paso. Propón un ejercicio corto al final."),
    11: ConfigEdad("11 años", "motivador",            "medio-alto",  600,
                   "Puedes usar vocabulario un poco más técnico pero siempre explicando. Relaciona el tema con situaciones reales de Colombia. Propón 1-2 ejercicios."),
    12: ConfigEdad("12 años", "tutor académico",      "estándar",    650,
                   "Habla como un tutor. Explica el concepto con precisión, muestra el procedimiento y propón ejercicios de práctica. Puedes mencionar por qué es importante aprender esto."),
}

# Edad por defecto si no se conoce
CONFIG_DEFAULT = ConfigEdad("sin especificar", "amigable", "medio", 500,
    "Adapta el lenguaje a un niño de primaria. Sé claro, paciente y motivador.")


# ─────────────────────────────────────────────
# DETECTOR DE SEÑALES DE RIESGO
# ─────────────────────────────────────────────
PALABRAS_RIESGO_ALTO = [
    "me quiero morir", "quiero morirme", "no quiero vivir", "quitarme la vida",
    "hacerme daño", "me voy a hacer daño", "me lastimo",
]
PALABRAS_RIESGO_MEDIO = [
    "me pegan", "me golpean", "me hacen daño", "me maltratan",
    "me hacen bullying", "matoneo", "me molestan", "me acosan",
    "tengo mucho miedo", "estoy muy triste", "lloro todo el tiempo",
    "no quiero ir al colegio", "odio el colegio", "me hacen la vida imposible",
    "nadie me quiere", "estoy solo", "estoy sola",
]
PALABRAS_EMOCION = [
    "triste", "asustado", "asustada", "miedo", "llorar",
    "nervioso", "nerviosa", "preocupado", "preocupada", "aburrido",
]


@dataclass
class AlertaBienestar:
    nivel:     str   # "alto", "medio", "emocion", "ninguno"
    detectado: list[str]
    mensaje_apoyo: str
    escalar: bool


def detectar_riesgo(texto: str) -> AlertaBienestar:
    """
    Analiza el mensaje del niño buscando señales de riesgo.
    Retorna una alerta con nivel y mensaje de apoyo apropiado.
    """
    texto_lower = texto.lower()

    # Nivel ALTO — riesgo inmediato
    detectados_alto = [p for p in PALABRAS_RIESGO_ALTO if p in texto_lower]
    if detectados_alto:
        return AlertaBienestar(
            nivel="alto",
            detectado=detectados_alto,
            mensaje_apoyo=(
                "Hola, lo que me contás es muy importante y quiero que sepas que no estás solo/a. "
                "Por favor habla ahora mismo con un adulto de confianza: tu mamá, papá, un profe o un familiar. "
                "Si necesitas ayuda urgente puedes llamar a la Línea 106 (gratuita, 24 horas). "
                "Estoy aquí contigo. 💙"
            ),
            escalar=True,
        )

    # Nivel MEDIO — situación preocupante
    detectados_medio = [p for p in PALABRAS_RIESGO_MEDIO if p in texto_lower]
    if detectados_medio:
        return AlertaBienestar(
            nivel="medio",
            detectado=detectados_medio,
            mensaje_apoyo=(
                "Lo que me contás me importa mucho. Nadie merece pasar por eso. "
                "¿Hay un adulto en quien confíes —tu mamá, papá, un profe— con quien puedas hablar hoy? "
                "También puedes llamar a la Línea 106, es gratis y confidencial. "
                "Recuerda: pedir ayuda es de valientes. 💙"
            ),
            escalar=True,
        )

    # Nivel EMOCIÓN — tristeza sin riesgo inmediato
    detectados_emo = [p for p in PALABRAS_EMOCION if p in texto_lower]
    if detectados_emo:
        return AlertaBienestar(
            nivel="emocion",
            detectado=detectados_emo,
            mensaje_apoyo=(
                "Oye, entiendo que no te sientes muy bien ahora. Está bien sentir eso. "
                "Si quieres contarme qué pasó, estoy aquí para escucharte. "
                "Y si prefieres, seguimos con la tarea juntos, eso también puede ayudar. 😊"
            ),
            escalar=False,
        )

    return AlertaBienestar(nivel="ninguno", detectado=[], mensaje_apoyo="", escalar=False)


# ─────────────────────────────────────────────
# CONSTRUCTOR DE PROMPTS
# ─────────────────────────────────────────────
SYSTEM_BASE = """Eres A.M.I.G.O. (Asistente Multimodal Inteligente para Guía y Orientación infantil), \
un tutor virtual amigable que ayuda a niños y niñas colombianas de 7 a 12 años con sus tareas y dudas escolares.

REGLAS FUNDAMENTALES:
1. NUNCA hagas la tarea por el niño. Guía, explica, da ejemplos y haz preguntas para que él/ella llegue a la respuesta.
2. Usa SIEMPRE un lenguaje cálido, paciente y motivador. Nunca hagas sentir al niño que su pregunta es tonta.
3. Adapta el vocabulario a la edad indicada.
4. Si detectas frustración ("no entiendo nada", "esto es imposible"), primero valida el sentimiento antes de explicar.
5. Usa ejemplos con cosas de Colombia: arepa, aguacate, chiva, partidos de fútbol, el río, la plaza del pueblo.
6. Responde SIEMPRE en español colombiano, informal pero respetuoso.
7. Si el niño pregunta algo que no es escolar, redirige amablemente hacia su tarea.
8. Termina siempre con una pregunta o reto corto para verificar la comprensión.
"""


def _config_edad(edad: Optional[int]) -> ConfigEdad:
    if edad is None:
        return CONFIG_DEFAULT
    # Si está fuera de rango, usar el más cercano
    if edad <= 7:  return CONFIGS_EDAD[7]
    if edad >= 12: return CONFIGS_EDAD[12]
    return CONFIGS_EDAD.get(edad, CONFIG_DEFAULT)


def construir_system_prompt(
    edad: Optional[int],
    perfil_regional: Optional[dict] = None,
    temas_rag: Optional[list] = None,
) -> str:
    """
    Construye el system prompt completo para el turno de conversación.
    Se llama una vez por sesión (o cuando cambia el contexto).
    """
    cfg = _config_edad(edad)
    partes = [SYSTEM_BASE]

    # ── Contexto de edad ──────────────────────────────────────────
    partes.append(f"""
EDAD DEL ESTUDIANTE: {cfg.rango}
TONO: {cfg.tono}
NIVEL DE COMPLEJIDAD: {cfg.complejidad}
INSTRUCCIONES ESPECÍFICAS PARA ESTA EDAD: {cfg.instruccion}
""")

    # ── Contexto regional ─────────────────────────────────────────
    if perfil_regional:
        municipio  = perfil_regional.get("municipio", "su municipio")
        nivel_mat  = perfil_regional.get("nivel_matematicas", "desconocido")
        nivel_lec  = perfil_regional.get("nivel_lectura", "desconocido")
        area_debil = perfil_regional.get("area_mas_debil", "general")
        desercion  = perfil_regional.get("tasa_desercion")

        contexto_regional = f"""
CONTEXTO TERRITORIAL (datos abiertos de datos.gov.co):
- Municipio del estudiante: {municipio}
- Nivel histórico en matemáticas en su región: {nivel_mat}
- Nivel histórico en lectura en su región: {nivel_lec}
- Área que más necesita refuerzo en su región: {area_debil}
"""
        if desercion is not None:
            contexto_regional += f"- Tasa de deserción escolar del municipio: {desercion}%\n"

        contexto_regional += f"""
INSTRUCCIÓN: Dado que el área más débil en {municipio} es {area_debil}, \
presta especial atención cuando el niño pregunte sobre ese tema y refuerza con paciencia extra.
"""
        partes.append(contexto_regional)

    # ── Contexto RAG — documentos reales de datos.gov.co ──────────
    if temas_rag:
        docs_str = "\n".join(
            f"  [{r.get('fuente', 'dato')}] {r.get('documento', '')}"
            for r in temas_rag[:5]
        )
        partes.append(f"""
CONTEXTO DE DATOS ABIERTOS (registros reales de datos.gov.co relevantes para esta pregunta):
{docs_str}

Usa estos datos reales como referencia para enriquecer tu explicación con información
del territorio del estudiante. No los leas textualmente — úsalos para dar contexto.
Siempre guía al niño con preguntas, nunca le des la respuesta directa.
""")

    return "\n".join(partes)


def construir_user_prompt(
    mensaje: str,
    alerta: Optional[AlertaBienestar] = None,
) -> str:
    """
    Construye el mensaje de usuario para enviar al LLM.
    Si hay alerta de emoción leve, agrega instrucción de empatía.
    """
    if alerta and alerta.nivel == "emocion":
        return (
            f"[El niño parece estar triste o preocupado. Primero valida su sentimiento "
            f"con empatía, luego ofrece ayuda con la tarea si quiere continuar.]\n\n"
            f"Mensaje del niño: {mensaje}"
        )
    return mensaje


def construir_mensaje_riesgo(alerta: AlertaBienestar) -> dict:
    """
    Devuelve la estructura de respuesta cuando hay riesgo medio o alto.
    La IA NO responde — el sistema entrega directamente el mensaje de apoyo.
    """
    return {
        "tipo":         "alerta_bienestar",
        "nivel":        alerta.nivel,
        "respuesta":    alerta.mensaje_apoyo,
        "escalar":      alerta.escalar,
        "palabras_clave": alerta.detectado,
    }


# ─────────────────────────────────────────────
# DETECTOR DE FRUSTRACIÓN
# ─────────────────────────────────────────────
FRASES_FRUSTRACION = [
    "no entiendo", "no puedo", "es muy difícil", "no sé nada",
    "esto es imposible", "me rindo", "no sirvo", "soy malo",
    "soy mala", "nunca aprendo", "odio las matemáticas",
    "no me gusta estudiar", "para qué sirve esto",
]

def detectar_frustracion(texto: str) -> bool:
    texto_lower = texto.lower()
    return any(f in texto_lower for f in FRASES_FRUSTRACION)


def mensaje_motivacion(edad: Optional[int] = None) -> str:
    """Devuelve un mensaje motivador adaptado a la edad."""
    if edad and edad <= 8:
        return "¡Oye, tranquilo/a! Todos nos equivocamos y así aprendemos. ¡Vamos paso a paso, tú puedes! 💪"
    if edad and edad <= 10:
        return "¡No te rindas! Lo difícil se vuelve fácil cuando lo practicamos. Te ayudo a entenderlo de una forma más sencilla. 😊"
    return "Entiendo que se siente frustrante cuando algo no sale. Eso es completamente normal. Vamos a verlo desde otro ángulo, ¿te parece? 💡"
