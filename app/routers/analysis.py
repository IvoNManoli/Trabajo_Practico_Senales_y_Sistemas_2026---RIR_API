"""Router para analisis completo de respuesta al impulso (M3).

Endpoints:
    POST /impulse-response  → parametros acusticos + curvas de Schroeder por banda
"""

import io

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.acoustic_parameters import calcular_parametros_acusticos
from app.services.signal_utils import cargar_audio

router = APIRouter()


@router.post("/impulse-response", summary="Analisis completo de una respuesta al impulso")
async def analizar_ri(
    file: UploadFile = File(..., description="Archivo WAV con la respuesta al impulso"),  # noqa: B008
) -> dict:
    """Analiza una RI y devuelve EDT, T10, T20, T30, D50, C80 y SNR por banda de octava."""
    try:
        ri, fs = cargar_audio(io.BytesIO(await file.read()))
    except Exception as e:
        raise HTTPException(
            status_code=422, detail=f"No se pudo leer el archivo de audio: {e}"
        ) from e
    if ri.ndim > 1:
        ri = ri[:, 0]

    if len(ri) < int(fs * 0.1):
        raise HTTPException(status_code=400, detail="La RI es demasiado corta (minimo 0.1 s)")

    try:
        parametros = calcular_parametros_acusticos(ri, fs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al calcular parametros: {e}") from e

    return {
        "duracion_s": round(len(ri) / fs, 4),
        "fs": fs,
        "parametros": {
            param: {str(int(fc)): v for fc, v in vals.items()}
            for param, vals in parametros.items()
        },
    }
