"""Router para analisis completo de respuesta al impulso (M3).

Endpoints:
    POST /impulse-response  → parametros acusticos + curvas de Schroeder por banda
"""

import io

import numpy as np
import soundfile as sf
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.acoustic_parameters import (
    calcular_parametros_acusticos,
    integral_schroeder,
)
from app.services.filter import filtro_octava

router = APIRouter()

_BANDAS: list[float] = [125.0, 250.0, 500.0, 1000.0, 2000.0, 4000.0]


@router.post("/impulse-response", summary="Analisis completo de una respuesta al impulso")
async def analizar_ri(
    file: UploadFile = File(..., description="Archivo WAV con la respuesta al impulso"),  # noqa: B008
) -> dict:
    """Analiza una RI y devuelve parametros ISO 3382 mas curvas de Schroeder por banda.

    Retorna EDT, T10, T20, T30, D50 y C80 para cada banda de octava, junto con
    las curvas de decaimiento de Schroeder para visualizacion.
    """
    try:
        contents = await file.read()
        buf = io.BytesIO(contents)
        ri, fs = sf.read(buf, dtype="float64", always_2d=False)
        if ri.ndim > 1:
            ri = ri[:, 0]
        fs = int(fs)
    except Exception as e:
        raise HTTPException(
            status_code=422, detail=f"No se pudo leer el archivo de audio: {e}"
        ) from e

    if len(ri) < int(fs * 0.1):
        raise HTTPException(status_code=400, detail="La RI es demasiado corta (minimo 0.1 s)")

    try:
        parametros = calcular_parametros_acusticos(ri, fs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al calcular parametros: {e}") from e

    schroeder_por_banda: dict = {}
    for fc in _BANDAS:
        ri_banda = filtro_octava(ri, fc=fc, fs=fs)
        edc = integral_schroeder(ri_banda)
        t = np.arange(len(edc)) / fs
        schroeder_por_banda[str(int(fc))] = {
            "tiempo": t.tolist(),
            "nivel_db": edc.tolist(),
        }

    params_serializados = {
        param: {str(int(fc)): v for fc, v in vals.items()}
        for param, vals in parametros.items()
    }

    return {
        "duracion_s": round(len(ri) / fs, 4),
        "fs": fs,
        "parametros": params_serializados,
        "schroeder": schroeder_por_banda,
    }
