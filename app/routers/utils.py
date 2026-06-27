"""Router para utilidades de procesamiento de senal (M2 + M3).

Endpoints:
    POST /schroeder   → curva de Schroeder de una RI
    POST /smoothing   → envolvente suavizada de una senal
    POST /log-scale   → senal convertida a escala logaritmica (dB)
"""

import io

import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.services.acoustic_parameters import integral_schroeder, suavizar_signal
from app.services.signal_utils import a_escala_log, cargar_audio

router = APIRouter()


@router.post("/schroeder", summary="Integral de Schroeder de una RI")
async def calcular_schroeder(
    file: UploadFile = File(..., description="Archivo WAV con la respuesta al impulso"),  # noqa: B008
) -> dict:
    """Calcula la curva de decaimiento energetico (EDC / integral de Schroeder) en dB."""
    try:
        ri, fs = cargar_audio(io.BytesIO(await file.read()))
    except Exception as e:
        raise HTTPException(
            status_code=422, detail=f"No se pudo leer el archivo de audio: {e}"
        ) from e
    if ri.ndim > 1:
        ri = ri[:, 0]
    edc = integral_schroeder(ri)
    t = np.arange(len(edc)) / fs
    return {
        "tiempo": t.tolist(),
        "nivel_db": edc.tolist(),
        "fs": fs,
    }


@router.post("/smoothing", summary="Suavizado de senal")
async def suavizar(
    file: UploadFile = File(..., description="Archivo WAV de entrada"),  # noqa: B008
    metodo: str = Form(
        default="hilbert",
        description="Metodo de suavizado: 'hilbert' o entero (tamano de ventana en muestras)",
    ),
) -> dict:
    """Suaviza una senal usando envolvente de Hilbert o media movil de energia."""
    try:
        signal, fs = cargar_audio(io.BytesIO(await file.read()))
    except Exception as e:
        raise HTTPException(
            status_code=422, detail=f"No se pudo leer el archivo de audio: {e}"
        ) from e
    if signal.ndim > 1:
        signal = signal[:, 0]
    try:
        ventana: int | str = int(metodo) if metodo != "hilbert" else "hilbert"
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="El metodo debe ser 'hilbert' o un entero (tamano de ventana)",
        ) from None
    envolvente = suavizar_signal(signal, ventana)
    t = np.arange(len(envolvente)) / fs
    return {
        "tiempo": t.tolist(),
        "envolvente": envolvente.tolist(),
        "fs": fs,
    }


@router.post("/log-scale", summary="Conversion a escala logaritmica (dB)")
async def escala_log(
    file: UploadFile = File(..., description="Archivo WAV de entrada"),  # noqa: B008
) -> dict:
    """Convierte una senal a escala logaritmica normalizada a 0 dB en el maximo."""
    try:
        signal, fs = cargar_audio(io.BytesIO(await file.read()))
    except Exception as e:
        raise HTTPException(
            status_code=422, detail=f"No se pudo leer el archivo de audio: {e}"
        ) from e
    if signal.ndim > 1:
        signal = signal[:, 0]
    nivel_db = a_escala_log(signal)
    t = np.arange(len(nivel_db)) / fs
    return {
        "tiempo": t.tolist(),
        "nivel_db": nivel_db.tolist(),
        "fs": fs,
    }
