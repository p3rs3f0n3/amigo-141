"""
A.M.I.G.O. — datos_service.py
==============================
Carga, LIMPIA y construye el perfil regional por municipio
a partir de los datasets de datos.gov.co.

Sigue el mismo patrón del notebook de capacitación:
  1. Cargar datos desde la API SODA
  2. Limpiar y normalizar (nulos, duplicados, tipos)
  3. Convertir cada fila en un documento de texto consultable
  4. Construir recuperador TF-IDF sobre esos documentos reales
  5. Armar perfil regional agregado por municipio

Datasets principales:
  - Saber 3°5°9°   (4h84-62xp) → desempeño primaria, público 7-12 años  ← PRINCIPAL
  - MEN municipio  (nudc-7mev) → cobertura, deserción, reprobación
  - MEN depto      (ji8i-4anb) → respaldo si faltan datos municipales
  - DIVIPOLA       (vafm-j2df) → coordenadas y código DANE
"""

import re
import unicodedata
import asyncio
import logging
import io
from typing import Optional

import numpy as np
import pandas as pd
import httpx
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("amigo.datos")

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────
BASE_URL = "https://www.datos.gov.co/resource"
TIMEOUT  = 30
LIMITE   = 5000

DATASETS = {
    "saber_359":     "4h84-62xp",
    "men_municipio": "nudc-7mev",
    "men_depto":     "ji8i-4anb",
    "divipola":      "vafm-j2df",
}

STOPWORDS_ES = [
    "a","al","algo","como","con","cual","de","del","dame","donde",
    "el","en","es","hay","la","las","lo","los","me","mi","para",
    "por","que","quiero","un","una","y","no","se","si","le","te",
    "son","hay","este","esta","eso","esa","municipio","colombia",
]

# Fallback cuando el portal está caído
FALLBACK_PERFILES = {
    "CALI": {
        "municipio": "CALI", "departamento": "VALLE DEL CAUCA",
        "cod_municipio": "76001",
        "nivel_matematicas": "medio", "nivel_lectura": "medio",
        "tasa_desercion": 3.2, "tasa_aprobacion": 88.5,
        "area_mas_debil": "matematicas",
        "latitud": 3.4516, "longitud": -76.5320,
        "fuente": "fallback_local",
    },
    "BOGOTA": {
        "municipio": "BOGOTA", "departamento": "BOGOTA D.C.",
        "cod_municipio": "11001",
        "nivel_matematicas": "alto", "nivel_lectura": "alto",
        "tasa_desercion": 2.1, "tasa_aprobacion": 91.0,
        "area_mas_debil": "ciencias",
        "latitud": 4.7110, "longitud": -74.0721,
        "fuente": "fallback_local",
    },
    "MEDELLIN": {
        "municipio": "MEDELLIN", "departamento": "ANTIOQUIA",
        "cod_municipio": "05001",
        "nivel_matematicas": "medio", "nivel_lectura": "alto",
        "tasa_desercion": 2.8, "tasa_aprobacion": 90.0,
        "area_mas_debil": "matematicas",
        "latitud": 6.2442, "longitud": -75.5812,
        "fuente": "fallback_local",
    },
}


# ═════════════════════════════════════════════
# 1. UTILIDADES DE TEXTO
# ═════════════════════════════════════════════
def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes, espacios limpios. Igual que en el notebook."""
    texto = str(texto).lower().strip()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = re.sub(r"\s+", " ", texto)
    return texto


def nivel_desempeno(puntaje: float) -> str:
    """Convierte puntaje numérico a nivel legible para el prompt de IA."""
    if puntaje >= 70: return "alto"
    if puntaje >= 50: return "medio"
    if puntaje >= 35: return "bajo"
    return "muy bajo"


# ═════════════════════════════════════════════
# 2. CARGA DESDE SODA
# ═════════════════════════════════════════════
async def _descargar(
    client: httpx.AsyncClient,
    dataset_id: str,
    limite: int = LIMITE,
) -> pd.DataFrame:
    """Descarga un dataset de datos.gov.co en formato CSV."""
    url = f"{BASE_URL}/{dataset_id}.csv"
    params = {"$limit": limite}
    try:
        r = await client.get(url, params=params, timeout=TIMEOUT)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text), dtype=str, low_memory=False)
        df.columns = [c.strip().lower() for c in df.columns]
        logger.info(f"✅ {dataset_id}: {len(df):,} filas | {len(df.columns)} columnas")
        return df
    except Exception as e:
        logger.warning(f"⚠️  No se pudo descargar {dataset_id}: {e}")
        return pd.DataFrame()


# ═════════════════════════════════════════════
# 3. LIMPIEZA DE DATOS
# ═════════════════════════════════════════════
def limpiar_dataset(df: pd.DataFrame, nombre: str) -> pd.DataFrame:
    """
    Limpieza estándar para cualquier dataset descargado de datos.gov.co.

    Pasos (siguiendo el notebook de capacitación):
      a) Estandarizar nombres de columnas
      b) Reemplazar vacíos y valores nulos
      c) Eliminar filas completamente vacías
      d) Eliminar duplicados exactos
      e) Reportar resultado
    """
    if df.empty:
        return df

    filas_antes = len(df)

    # a) Nombres de columna: minúsculas, sin espacios extra
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # b) Reemplazar cadenas vacías, "nan", "none", "null" por NaN real
    df.replace(
        to_replace=["", "nan", "none", "null", "n/a", "n.a.", "-", "nd", "s/d"],
        value=pd.NA,
        inplace=True,
    )

    # c) Eliminar columnas que son 100% nulas (no aportan nada)
    cols_antes = len(df.columns)
    df.dropna(axis=1, how="all", inplace=True)
    cols_eliminadas = cols_antes - len(df.columns)
    if cols_eliminadas:
        logger.info(f"  [{nombre}] Columnas 100% vacías eliminadas: {cols_eliminadas}")

    # d) Eliminar filas completamente vacías
    df.dropna(axis=0, how="all", inplace=True)

    # e) Eliminar duplicados exactos
    dups = df.duplicated().sum()
    if dups:
        df.drop_duplicates(inplace=True)
        logger.info(f"  [{nombre}] Duplicados eliminados: {dups}")

    # f) Rellenar NaN restantes con cadena vacía para manejo uniforme
    df.fillna("", inplace=True)
    df = df.astype(str)

    filas_despues = len(df)
    logger.info(
        f"  [{nombre}] Limpieza: {filas_antes:,} → {filas_despues:,} filas "
        f"({filas_antes - filas_despues} eliminadas) | {len(df.columns)} columnas finales"
    )
    return df


def reporte_calidad(df: pd.DataFrame, nombre: str) -> dict:
    """
    Genera un reporte rápido de calidad del dataset.
    Útil para la documentación del concurso (evidencia de análisis).
    """
    if df.empty:
        return {"dataset": nombre, "estado": "vacío"}

    total_celdas = df.shape[0] * df.shape[1]
    vacios = (df == "").sum().sum()
    pct_vacios = round(vacios / total_celdas * 100, 1) if total_celdas else 0

    reporte = {
        "dataset":        nombre,
        "filas":          len(df),
        "columnas":       len(df.columns),
        "celdas_vacias":  int(vacios),
        "pct_vacias":     pct_vacios,
        "columnas_lista": list(df.columns),
    }
    logger.info(
        f"  📊 [{nombre}] Calidad: {pct_vacios}% celdas vacías "
        f"| columnas: {list(df.columns)[:6]}..."
    )
    return reporte


# ═════════════════════════════════════════════
# 4. CONVERSIÓN DE FILAS A DOCUMENTOS
#    (igual que el notebook: cada fila → texto consultable)
# ═════════════════════════════════════════════

# Columnas relevantes de Saber 3°5°9° para el documento
COLS_SABER_DOC = [
    "cole_mcpio_ubicacion", "cole_depto_ubicacion",
    "grado", "periodo",
    "punt_matematicas", "punt_lenguaje", "punt_ciencias",
    "cole_naturaleza", "cole_area_ubicacion",
    "fami_estratovivienda",
]

# Columnas relevantes de MEN municipio para el documento
COLS_MEN_DOC = [
    "entidad_territorial", "municipio", "nombre_municipio",
    "anno", "año", "anio",
    "tasa_desercion_intraanual", "tasa_aprobacion",
    "tasa_reprobacion", "tasa_repitencia",
    "cobertura_bruta", "cobertura_neta",
]

# Etiquetas legibles para cada campo
ETIQUETAS = {
    "cole_mcpio_ubicacion":     "Municipio",
    "cole_depto_ubicacion":     "Departamento",
    "grado":                    "Grado",
    "periodo":                  "Periodo",
    "punt_matematicas":         "Puntaje matemáticas",
    "punt_lenguaje":            "Puntaje lenguaje",
    "punt_ciencias":            "Puntaje ciencias",
    "cole_naturaleza":          "Naturaleza colegio",
    "cole_area_ubicacion":      "Zona",
    "fami_estratovivienda":     "Estrato",
    "entidad_territorial":      "Entidad territorial",
    "municipio":                "Municipio",
    "nombre_municipio":         "Municipio",
    "anno":                     "Año",
    "año":                      "Año",
    "anio":                     "Año",
    "tasa_desercion_intraanual":"Tasa deserción",
    "tasa_aprobacion":          "Tasa aprobación",
    "tasa_reprobacion":         "Tasa reprobación",
    "tasa_repitencia":          "Tasa repitencia",
    "cobertura_bruta":          "Cobertura bruta",
    "cobertura_neta":           "Cobertura neta",
}


def fila_a_documento(row: pd.Series, cols_preferidas: list[str]) -> str:
    """
    Convierte una fila del dataset en un texto consultable.
    Solo incluye las columnas que existen y tienen valor.

    Ejemplo de salida:
      'Municipio: CALI | Departamento: VALLE DEL CAUCA | Grado: 5 |
       Puntaje matemáticas: 312 | Puntaje lenguaje: 298 | Zona: Urbana'
    """
    partes = []
    cols_existentes = [c for c in cols_preferidas if c in row.index]

    # Si no hay ninguna de las cols preferidas, usar todas las disponibles
    if not cols_existentes:
        cols_existentes = list(row.index)

    for col in cols_existentes:
        val = str(row.get(col, "")).strip()
        if val and val.lower() not in ("", "nan", "none", "null"):
            etiqueta = ETIQUETAS.get(col, col.replace("_", " ").title())
            partes.append(f"{etiqueta}: {val}")

    return " | ".join(partes)


def construir_biblioteca(df: pd.DataFrame, cols_doc: list[str], nombre: str) -> pd.DataFrame:
    """
    Agrega la columna 'documento' al dataframe:
    cada fila se convierte en texto consultable para el RAG.
    También agrega 'documento_normalizado' para el vectorizador.
    """
    if df.empty:
        return df

    df = df.copy()
    df["documento"] = df.apply(
        lambda row: fila_a_documento(row, cols_doc), axis=1
    )
    df["documento_normalizado"] = df["documento"].apply(normalizar)

    # Eliminar filas cuyo documento quedó vacío
    df = df[df["documento"].str.strip() != ""]

    logger.info(f"  📚 [{nombre}] Biblioteca: {len(df):,} documentos generados")
    return df


# ═════════════════════════════════════════════
# 5. RECUPERADOR RAG SOBRE DATOS REALES
# ═════════════════════════════════════════════
class RecuperadorRAG:
    """
    Recuperador TF-IDF + coseno sobre los documentos generados
    de los datasets reales de datos.gov.co.
    Sigue exactamente el patrón del notebook de capacitación.
    """

    def __init__(self, df: pd.DataFrame, nombre: str = "dataset"):
        self.nombre = nombre
        self.df = df.reset_index(drop=True)
        self.vectorizer = TfidfVectorizer(
            preprocessor=normalizar,
            ngram_range=(1, 2),
            stop_words=STOPWORDS_ES,
            min_df=1,
        )
        if not df.empty and "documento_normalizado" in df.columns:
            self.X = self.vectorizer.fit_transform(df["documento_normalizado"])
            logger.info(f"✅ RAG [{nombre}]: {len(df):,} docs | matriz {self.X.shape}")
        else:
            self.X = None
            logger.warning(f"⚠️  RAG [{nombre}]: sin datos para vectorizar")

    def buscar(self, pregunta: str, k: int = 5, min_score: float = 0.01) -> pd.DataFrame:
        """
        Devuelve las k filas más relevantes para la pregunta.
        Incluye columna 'score' de similitud.
        """
        if self.X is None or self.df.empty:
            return pd.DataFrame()

        qvec = self.vectorizer.transform([normalizar(pregunta)])
        scores = cosine_similarity(qvec, self.X).ravel()
        idx = np.argsort(scores)[::-1][:k]
        resultado = self.df.iloc[idx].copy()
        resultado["score"] = scores[idx]
        return resultado[resultado["score"] >= min_score]

    def buscar_por_municipio(self, municipio: str, k: int = 20) -> pd.DataFrame:
        """Filtro directo por municipio en el documento (más preciso para perfiles)."""
        if self.df.empty:
            return pd.DataFrame()
        mun_norm = normalizar(municipio)
        mask = self.df["documento_normalizado"].str.contains(mun_norm, regex=False)
        return self.df[mask].head(k)


# ═════════════════════════════════════════════
# 6. CONSTRUCCIÓN DEL PERFIL REGIONAL
# ═════════════════════════════════════════════
def _col_numerica(df: pd.DataFrame, palabras_clave: list[str]) -> Optional[str]:
    """Busca la primera columna cuyo nombre contenga alguna de las palabras clave."""
    for col in df.columns:
        if any(p in col for p in palabras_clave):
            return col
    return None


def _col_municipio(df: pd.DataFrame) -> Optional[str]:
    """Detecta la columna de municipio (varía por dataset)."""
    candidatas = [
        "cole_mcpio_ubicacion", "nombre_municipio", "municipio",
        "entidad_territorial", "nom_municipio", "mpio_nombre",
    ]
    return next((c for c in candidatas if c in df.columns), None)


def construir_perfil(
    municipio: str,
    df_saber: pd.DataFrame,
    df_men: pd.DataFrame,
) -> dict:
    """
    Construye el perfil regional de un municipio a partir de los datos limpios.
    """
    perfil: dict = {
        "municipio":         municipio.upper(),
        "nivel_matematicas": "desconocido",
        "nivel_lectura":     "desconocido",
        "area_mas_debil":    "general",
        "tasa_desercion":    None,
        "tasa_aprobacion":   None,
        "n_registros_saber": 0,
        "fuente":            "datos_abiertos",
    }

    # ── Saber 3°5°9° ─────────────────────────────────────────────
    if not df_saber.empty:
        col_mun = _col_municipio(df_saber)
        if col_mun:
            mun_norm = normalizar(municipio)
            mask = df_saber[col_mun].apply(normalizar).str.contains(mun_norm, regex=False)
            df_m = df_saber[mask]
        else:
            df_m = pd.DataFrame()

        if not df_m.empty:
            perfil["n_registros_saber"] = len(df_m)
            col_mat = _col_numerica(df_m, ["matema", "matematica"])
            col_lec = _col_numerica(df_m, ["lectura", "lenguaje"])

            promedios = {}
            for area, col in [("matematicas", col_mat), ("lectura", col_lec)]:
                if col:
                    val = pd.to_numeric(df_m[col], errors="coerce").mean()
                    if not np.isnan(val):
                        promedios[area] = round(float(val), 1)
                        perfil[f"nivel_{area}"] = nivel_desempeno(val)
                        perfil[f"prom_{area}_raw"] = round(float(val), 1)

            # Área más débil: la de menor puntaje
            if promedios:
                area_debil = min(promedios, key=promedios.get)
                perfil["area_mas_debil"] = area_debil

    # ── MEN municipio ─────────────────────────────────────────────
    if not df_men.empty:
        col_mun = _col_municipio(df_men)
        if col_mun:
            mun_norm = normalizar(municipio)
            mask = df_men[col_mun].apply(normalizar).str.contains(mun_norm, regex=False)
            df_m = df_men[mask]
        else:
            df_m = pd.DataFrame()

        if not df_m.empty:
            col_des = _col_numerica(df_m, ["deserc"])
            col_apr = _col_numerica(df_m, ["aprobac"])
            for campo, col in [("tasa_desercion", col_des), ("tasa_aprobacion", col_apr)]:
                if col:
                    val = pd.to_numeric(df_m[col], errors="coerce").mean()
                    if not np.isnan(val):
                        perfil[campo] = round(float(val), 2)

    return perfil


# ═════════════════════════════════════════════
# 7. SERVICIO PRINCIPAL
# ═════════════════════════════════════════════
class DatosService:
    """
    Servicio central de datos para A.M.I.G.O.

    Flujo completo:
      cargar_datasets() → limpiar → construir_biblioteca() → RAG listo
      obtener_perfil_regional(mun) → construir_perfil() con datos reales
      buscar_contexto(pregunta, mun) → RecuperadorRAG.buscar()
    """

    def __init__(self):
        self._df_saber:   pd.DataFrame = pd.DataFrame()
        self._df_men:     pd.DataFrame = pd.DataFrame()
        self._rag_saber:  Optional[RecuperadorRAG] = None
        self._rag_men:    Optional[RecuperadorRAG] = None
        self._cache_perfiles: dict[str, dict] = {}
        self._cargado = False
        self.reportes_calidad: list[dict] = []

    async def cargar_datasets(self):
        """
        Descarga, limpia y construye la biblioteca de documentos.
        Se llama una sola vez al iniciar el servidor.
        """
        if self._cargado:
            return

        logger.info("⬇️  Descargando datasets de datos.gov.co ...")
        async with httpx.AsyncClient(follow_redirects=True) as client:
            df_saber_raw, df_men_raw = await asyncio.gather(
                _descargar(client, DATASETS["saber_359"],     limite=LIMITE),
                _descargar(client, DATASETS["men_municipio"], limite=LIMITE),
            )

        # ── Limpieza ──────────────────────────────────────────────
        logger.info("🧹 Limpiando datasets ...")
        self._df_saber = limpiar_dataset(df_saber_raw, "Saber_359")
        self._df_men   = limpiar_dataset(df_men_raw,   "MEN_municipio")

        # ── Reporte de calidad ────────────────────────────────────
        self.reportes_calidad = [
            reporte_calidad(self._df_saber, "Saber_3_5_9"),
            reporte_calidad(self._df_men,   "MEN_municipio"),
        ]

        # ── Biblioteca de documentos (una fila = un documento) ────
        logger.info("📚 Construyendo biblioteca de documentos ...")
        self._df_saber = construir_biblioteca(self._df_saber, COLS_SABER_DOC, "Saber_359")
        self._df_men   = construir_biblioteca(self._df_men,   COLS_MEN_DOC,   "MEN_municipio")

        # ── Recuperadores RAG ─────────────────────────────────────
        logger.info("🔍 Construyendo índices TF-IDF ...")
        self._rag_saber = RecuperadorRAG(self._df_saber, "Saber_359")
        self._rag_men   = RecuperadorRAG(self._df_men,   "MEN_municipio")

        self._cargado = True
        logger.info("✅ Backend de datos listo")

    async def obtener_perfil_regional(self, municipio: str) -> dict:
        """
        Devuelve el perfil regional del municipio.
        Usa caché en memoria para no recalcular en cada mensaje.
        """
        mun_key = municipio.upper().strip()
        if mun_key in self._cache_perfiles:
            return self._cache_perfiles[mun_key]

        if not self._cargado:
            await self.cargar_datasets()

        if self._df_saber.empty and self._df_men.empty:
            logger.warning(f"Datasets vacíos — usando fallback para {mun_key}")
            perfil = FALLBACK_PERFILES.get(mun_key, {
                "municipio": mun_key, "departamento": "Colombia",
                "nivel_matematicas": "medio", "nivel_lectura": "medio",
                "area_mas_debil": "general", "fuente": "fallback_generico",
            })
        else:
            perfil = construir_perfil(mun_key, self._df_saber, self._df_men)

        self._cache_perfiles[mun_key] = perfil
        return perfil

    def buscar_contexto(
        self,
        pregunta: str,
        municipio: Optional[str] = None,
        k: int = 5,
    ) -> list[dict]:
        """
        Busca los registros más relevantes de los datasets reales
        para la pregunta del niño. Combina Saber + MEN.

        Si se pasa municipio, filtra primero por él para dar
        contexto más preciso al LLM.
        """
        resultados = []

        for rag, nombre in [(self._rag_saber, "saber"), (self._rag_men, "men")]:
            if rag is None:
                continue

            # Si hay municipio, buscar primero registros de ese municipio
            if municipio:
                df_mun = rag.buscar_por_municipio(municipio, k=k * 2)
                if not df_mun.empty:
                    # Dentro de los registros del municipio, rankear por pregunta
                    qvec = rag.vectorizer.transform([normalizar(pregunta)])
                    idx_mun = df_mun.index.tolist()
                    scores_mun = cosine_similarity(
                        qvec, rag.X[idx_mun]
                    ).ravel()
                    top_idx = np.argsort(scores_mun)[::-1][:k]
                    for i in top_idx:
                        fila = df_mun.iloc[i]
                        resultados.append({
                            "fuente":    nombre,
                            "documento": fila.get("documento", ""),
                            "score":     round(float(scores_mun[i]), 3),
                        })
                    continue

            # Si no hay municipio o no hubo resultados locales, buscar global
            df_res = rag.buscar(pregunta, k=k)
            for _, fila in df_res.iterrows():
                resultados.append({
                    "fuente":    nombre,
                    "documento": fila.get("documento", ""),
                    "score":     round(float(fila.get("score", 0)), 3),
                })

        # Ordenar por score descendente y devolver top k
        resultados.sort(key=lambda x: x["score"], reverse=True)
        return resultados[:k]

    def limpiar_cache(self):
        self._cache_perfiles.clear()
        self._cargado = False
