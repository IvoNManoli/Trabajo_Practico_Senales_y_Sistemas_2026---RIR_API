"""Router para calculo de parametros acusticos (M3).

Endpoints:
    POST /parameters           → parametros ISO 3382 por banda (keyed by parametro)
    POST /parameters/by-bands  → mismo resultado reorganizado por banda
"""

import io

import soundfile as sf
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.acoustic_parameters import calcular_parametros_acusticos

router = APIRouter()


async def _leer_ri(file: UploadFile) -> tuple:
    """Lee una RI desde un archivo WAV subido via multipart."""
    try:
        contents = await file.read()
        buf = io.BytesIO(contents)
        signal, fs = sf.read(buf, dtype="float64", always_2d=False)
        if signal.ndim > 1:
            signal = signal[:, 0]
        return signal, int(fs)
    except Exception as e:
        raise HTTPException(
            status_code=422, detail=f"No se pudo leer el archivo de audio: {e}"
        ) from e


def _serializar_params(params: dict) -> dict:
    """Convierte las claves float de frecuencia a str para serializacion JSON."""
    return {param: {str(int(fc)): v for fc, v in vals.items()} for param, vals in params.items()}


@router.post("/parameters", summary="Calcula parametros acusticos ISO 3382")
async def calcular_parametros(
    file: UploadFile = File(..., description="Archivo WAV con la respuesta al impulso"),  # noqa: B008
) -> dict:
    """Calcula EDT, T10, T20, T30, D50 y C80 por banda de octava segun ISO 3382."""
    ri, fs = await _leer_ri(file)
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
    ri, fs = await _leer_ri(file)
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
