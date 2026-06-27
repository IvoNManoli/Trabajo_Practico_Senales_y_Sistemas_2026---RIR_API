"""Router para calculo de parametros acusticos (M3).

Endpoints:
    POST /parameters           → parametros ISO 3382 por banda (keyed by parametro)
    POST /parameters/by-bands  → mismo resultado reorganizado por banda
"""

import io

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.acoustic_parameters import calcular_parametros_acusticos
from app.services.signal_utils import cargar_audio

router = APIRouter()


def _serializar_params(params: dict) -> dict:
    """Convierte las claves float de frecuencia a str para serializacion JSON."""
    return {param: {str(int(fc)): v for fc, v in vals.items()} for param, vals in params.items()}


@router.post("/parameters", summary="Calcula parametros acusticos ISO 3382")
async def calcular_parametros(
    file: UploadFile = File(..., description="Archivo WAV con la respuesta al impulso"),  # noqa: B008
) -> dict:
    """Calcula EDT, T10, T20, T30, D50 y C80 por banda de octava segun ISO 3382."""
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
        params = calcular_parametros_acusticos(ri, fs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al calcular parametros: {e}") from e
    return _serializar_params(params)


@router.post("/parameters/by-bands", summary="Parametros acusticos reorganizados por banda")
async def calcular_parametros_por_bandas(
    file: UploadFile = File(..., description="Archivo WAV con la respuesta al impulso"),  # noqa: B008
) -> dict:
    """Mismo calculo que /parameters pero el resultado esta organizado por frecuencia de banda."""
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
        params = calcular_parametros_acusticos(ri, fs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al calcular parametros: {e}") from e

    bandas: dict = {}
    for parametro, valores in params.items():
        for fc, val in valores.items():
            key = str(int(fc))
            if key not in bandas:
                bandas[key] = {}
            bandas[key][parametro] = val
    return {"bandas_hz": bandas}
