"""Router para calculo de parametros acusticos (M3).

Endpoints:
    POST /parameters           → un valor global por parametro (promedio 500+1000 Hz)
    POST /parameters/by-bands  → mismo calculo, detallado por banda
"""

import io

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.acoustic_parameters import calcular_parametros_acusticos
from app.services.signal_utils import cargar_audio

router = APIRouter()

_BANDAS_GLOBAL = (500.0, 1000.0)


def _serializar_params(params: dict) -> dict:
    """Convierte las claves float de frecuencia a str para serializacion JSON."""
    return {param: {str(int(fc)): v for fc, v in vals.items()} for param, vals in params.items()}


def _promedio_500_1000(valores: dict[float, float | None]) -> float | None:
    """Reduce un parametro por banda a un unico valor global.

    Promedia las bandas de 500 Hz y 1000 Hz, la convencion habitual en acustica
    para reportar un tiempo de reverberacion (u otro parametro) representativo
    sin desglosar por banda. Si alguna de las dos falta (por ejemplo, un ajuste
    con R^2 insuficiente), se usa la que este disponible; si faltan las dos, el
    resultado es None.
    """
    disponibles = [valores[fc] for fc in _BANDAS_GLOBAL if valores.get(fc) is not None]
    if not disponibles:
        return None
    return sum(disponibles) / len(disponibles)


@router.post("/parameters", summary="Calcula parametros acusticos ISO 3382 (valor global)")
async def calcular_parametros(
    file: UploadFile = File(..., description="Archivo WAV con la respuesta al impulso"),  # noqa: B008
) -> dict:
    """Calcula EDT, T10, T20, T30, D50 y C80 como un valor global por parametro.

    El valor global es el promedio de las bandas de 500 Hz y 1000 Hz. Para el
    detalle completo por banda de octava, usar `/parameters/by-bands`.
    """
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
    return {parametro: _promedio_500_1000(valores) for parametro, valores in params.items()}


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
