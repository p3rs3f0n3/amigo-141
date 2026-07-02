"""
A.M.I.G.O. — tests/test_model_inference.py
============================================
Pruebas de consistencia del detector de riesgo y el constructor de prompts.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from prompt_builder import (
    detectar_riesgo, detectar_frustracion,
    construir_system_prompt, CONFIGS_EDAD
)


def test_detector_riesgo_alto():
    alerta = detectar_riesgo("me quiero morir")
    assert alerta.nivel == "alto"
    assert alerta.escalar == True
    print("✅ test_detector_riesgo_alto OK")


def test_detector_riesgo_medio():
    alerta = detectar_riesgo("me hacen bullying en el colegio")
    assert alerta.nivel == "medio"
    assert alerta.escalar == True
    print("✅ test_detector_riesgo_medio OK")


def test_detector_riesgo_emocion():
    alerta = detectar_riesgo("estoy un poco triste hoy")
    assert alerta.nivel == "emocion"
    assert alerta.escalar == False
    print("✅ test_detector_riesgo_emocion OK")


def test_detector_riesgo_ninguno():
    alerta = detectar_riesgo("no entiendo las fracciones")
    assert alerta.nivel == "ninguno"
    print("✅ test_detector_riesgo_ninguno OK")


def test_detector_frustracion():
    assert detectar_frustracion("no entiendo nada de esto") == True
    assert detectar_frustracion("me rindo, es imposible") == True
    assert detectar_frustracion("cuánto es 5 por 3") == False
    print("✅ test_detector_frustracion OK")


def test_configs_edad_completas():
    for edad in range(7, 13):
        cfg = CONFIGS_EDAD[edad]
        assert cfg.max_tokens > 0
        assert cfg.instruccion != ""
    print("✅ test_configs_edad_completas OK")


def test_system_prompt_contiene_contexto():
    perfil = {
        "municipio": "CALI",
        "nivel_matematicas": "bajo",
        "nivel_lectura": "medio",
        "area_mas_debil": "matematicas",
        "tasa_desercion": 3.2,
    }
    system = construir_system_prompt(edad=10, perfil_regional=perfil)
    assert "CALI" in system
    assert "matematicas" in system
    assert "10 años" in system
    print("✅ test_system_prompt_contiene_contexto OK")


if __name__ == "__main__":
    test_detector_riesgo_alto()
    test_detector_riesgo_medio()
    test_detector_riesgo_emocion()
    test_detector_riesgo_ninguno()
    test_detector_frustracion()
    test_configs_edad_completas()
    test_system_prompt_contiene_contexto()
    print("\n✅ Todos los tests de inferencia pasaron")
