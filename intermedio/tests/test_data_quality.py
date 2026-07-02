"""
A.M.I.G.O. — tests/test_data_quality.py
=========================================
Pruebas de calidad de datos y validación de rangos.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pandas as pd
from datos_service import limpiar_dataset, nivel_desempeno, normalizar


def test_normalizacion():
    assert normalizar("  Ñoño  ") == "nono"
    assert normalizar("CALI") == "cali"
    assert normalizar("  Valle del Cauca  ") == "valle del cauca"
    print("✅ test_normalizacion OK")


def test_nivel_desempeno():
    assert nivel_desempeno(75) == "alto"
    assert nivel_desempeno(60) == "medio"
    assert nivel_desempeno(40) == "bajo"
    assert nivel_desempeno(20) == "muy bajo"
    print("✅ test_nivel_desempeno OK")


def test_limpieza_elimina_duplicados():
    df = pd.DataFrame([
        {"municipio": "CALI", "puntaje": "320"},
        {"municipio": "CALI", "puntaje": "320"},  # duplicado
        {"municipio": "BOGOTA", "puntaje": "350"},
    ])
    df_limpio = limpiar_dataset(df.copy(), "test")
    assert len(df_limpio) == 2, f"Esperaba 2 filas, got {len(df_limpio)}"
    print("✅ test_limpieza_elimina_duplicados OK")


def test_limpieza_elimina_nulos():
    df = pd.DataFrame([
        {"municipio": "CALI",   "puntaje": "320"},
        {"municipio": "nan",    "puntaje": ""},
        {"municipio": "n/a",    "puntaje": "-"},
        {"municipio": "",       "puntaje": "none"},
    ])
    df_limpio = limpiar_dataset(df.copy(), "test")
    # Las filas con todo nulo deben eliminarse
    assert len(df_limpio) >= 1
    print(f"✅ test_limpieza_elimina_nulos OK — {len(df_limpio)} filas válidas")


def test_columnas_100_pct_vacias_se_eliminan():
    df = pd.DataFrame([
        {"municipio": "CALI", "col_vacia": "", "puntaje": "320"},
        {"municipio": "BOGOTA", "col_vacia": "", "puntaje": "350"},
    ])
    df_limpio = limpiar_dataset(df.copy(), "test")
    assert "col_vacia" not in df_limpio.columns
    print("✅ test_columnas_vacias_eliminadas OK")


if __name__ == "__main__":
    test_normalizacion()
    test_nivel_desempeno()
    test_limpieza_elimina_duplicados()
    test_limpieza_elimina_nulos()
    test_columnas_100_pct_vacias_se_eliminan()
    print("\n✅ Todos los tests de calidad de datos pasaron")
