"""Router para filtrado por bandas de octava (M2 + M3).

Endpoints:
    GET  /frequencies  → lista de frecuencias centrales disponibles
    POST /band         → WAV filtrado por banda de octava
"""

import io

import soundfile as sf
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.services.filter import filtro_octava

router = APIRouter()

_FRECUENCIAS_DISPONIBLES: list[float] = [
    31.5, 63.0, 125.0, 250.0, 500.0, 1000.0, 2000.0, 4000.0, 8000.0, 16000.0,
]


@router.get("/frequencies", summary="Lista frecuencias centrales disponibles")
async def obtener_frecuencias() -> dict:
    """Devuelve las frecuencias centrales de bandas de octava disponibles para filtrado."""
    return {"frecuencias": _FRECUENCIAS_DISPONIBLES}


@router.post("/band", summary="Filtra audio por banda de octava")
async def filtrar_banda(
    file: UploadFile = File(..., description="Archivo WAV de entrada"),
    fc: float = Form(..., description="Frecuencia central de la banda en Hz"),
) -> StreamingResponse:
    """Aplica un filtro pasabanda de una octava (Butterworth orden 4, fase cero) al audio."""
    if fc not in _FRECUENCIAS_DISPONIBLES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Frecuencia {fc} Hz no disponible. "
                f"Frecuencias validas: {_FRECUENCIAS_DISPONIBLES}"
            ),
        )
    try:
        contents = await file.read()
        buf = io.BytesIO(contents)
        signal, fs = sf.read(buf, dtype="float64", always_2d=False)
        if signal.ndim > 1:
            signal = signal[:, 0]
        fs = int(fs)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"No se pudo leer el archivo de audio: {e}")

    filtered = filtro_octava(signal, fc=fc, fs=fs)

    out_buf = io.BytesIO()
    sf.write(out_buf, filtered, fs, format="WAV", subtype="PCM_16")
    out_buf.seek(0)
    return StreamingResponse(
        out_buf,
        media_type="audio/wav",
        headers={"Content-Disposition": f'attachment; filename="filtered_{int(fc)}hz.wav"'},
    )
