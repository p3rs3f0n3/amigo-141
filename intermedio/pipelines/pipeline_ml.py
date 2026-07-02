"""
A.M.I.G.O. — pipelines/pipeline_ml.py
=======================================
Pipeline completo: descarga → limpieza → biblioteca → RAG → perfil.
Puede correrse de forma independiente para generar los artefactos
que luego usa el backend en tiempo de ejecución.

Uso:
    python pipelines/pipeline_ml.py
    python pipelines/pipeline_ml.py --municipio CALI
"""

import sys
import os
import asyncio
import argparse
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from datos_service import (
    DatosService, limpiar_dataset, reporte_calidad,
    construir_biblioteca, COLS_SABER_DOC, COLS_MEN_DOC
)


async def run_pipeline(municipio: str = None):
    print("=" * 60)
    print("  A.M.I.G.O. — Pipeline ML")
    print("=" * 60)

    svc = DatosService()

    # ── Paso 1: Descarga ──────────────────────────────────────────
    print("\n📥 Paso 1: Descargando datasets de datos.gov.co ...")
    await svc.cargar_datasets()

    # ── Paso 2: Reportes de calidad ───────────────────────────────
    print("\n📊 Paso 2: Reporte de calidad de datos")
    for rep in svc.reportes_calidad:
        print(f"  [{rep['dataset']}]")
        print(f"    Filas    : {rep.get('filas', 'N/A'):,}" if isinstance(rep.get('filas'), int) else f"    Filas    : {rep.get('filas', 'N/A')}")
        print(f"    Columnas : {rep.get('columnas', 'N/A')}")
        print(f"    % vacíos : {rep.get('pct_vacias', 'N/A')}%")

    # ── Paso 3: Perfil regional ───────────────────────────────────
    municipios_prueba = [municipio] if municipio else ["CALI", "BOGOTA", "MEDELLIN"]
    print(f"\n🗺️  Paso 3: Generando perfiles regionales para {municipios_prueba}")
    perfiles = {}
    for mun in municipios_prueba:
        perfil = await svc.obtener_perfil_regional(mun)
        perfiles[mun] = perfil
        print(f"\n  {mun}:")
        print(f"    Matemáticas : {perfil['nivel_matematicas']}")
        print(f"    Lectura     : {perfil['nivel_lectura']}")
        print(f"    Área débil  : {perfil['area_mas_debil']}")
        print(f"    Deserción   : {perfil.get('tasa_desercion', 'N/A')}%")
        print(f"    Fuente      : {perfil['fuente']}")

    # ── Paso 4: Guardar outputs ───────────────────────────────────
    output_dir = Path(__file__).parent.parent / "data" / "04_model_output"
    output_dir.mkdir(parents=True, exist_ok=True)

    perfiles_path = output_dir / "perfiles_regionales.json"
    with open(perfiles_path, "w", encoding="utf-8") as f:
        json.dump(perfiles, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Perfiles guardados en {perfiles_path}")

    calidad_path = output_dir / "reporte_calidad.json"
    with open(calidad_path, "w", encoding="utf-8") as f:
        json.dump(svc.reportes_calidad, f, ensure_ascii=False, indent=2, default=str)
    print(f"💾 Reporte de calidad guardado en {calidad_path}")

    print("\n" + "=" * 60)
    print("  ✅ Pipeline completado")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline ML de A.M.I.G.O.")
    parser.add_argument("--municipio", type=str, help="Municipio específico a procesar")
    args = parser.parse_args()
    asyncio.run(run_pipeline(args.municipio))
