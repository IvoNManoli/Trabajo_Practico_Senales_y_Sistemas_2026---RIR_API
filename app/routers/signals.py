"""Router para generacion de senales (M1 + M3).

Endpoints:
    POST /pink-noise       → WAV de ruido rosa
    POST /sine-sweep       → WAV de sine sweep logaritmico
    POST /synthetic-ir     → WAV de RI sintetica con T60 por banda
"""

import io

import soundfile as sf
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.signals import PinkNoiseRequest, SineSweepRequest, SyntheticIRRequest
from app.services.pink_noise import generar_ruido_rosa
from app.services.signal_utils import sintetizar_ri
from app.services.sine_sweep import generar_sine_sweep

router = APIRouter()


def _wav_response(signal, fs: int, filename: str = "output.wav") -> StreamingResponse:
    """Convierte una senal numpy a una respuesta HTTP con WAV."""
    buf = io.BytesIO()
    sf.write(buf, signal, fs, format="WAV", subtype="PCM_16")
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="audio/wav",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/pink-noise", summary="Genera ruido rosa")
async def generar_ruido_rosa_endpoint(req: PinkNoiseRequest) -> StreamingResponse:
    """Genera una senal de ruido rosa (densidad espectral 1/f) y la devuelve como WAV."""
    signal = generar_ruido_rosa(req.duracion, req.fs)
    return _wav_response(signal, req.fs, "pink_noise.wav")


@router.post("/sine-sweep", summary="Genera sine sweep logaritmico")
async def generar_sine_sweep_endpoint(req: SineSweepRequest) -> StreamingResponse:
    """Genera un barrido senoidal logaritmico segun Farina (2000) y lo devuelve como WAV."""
    if req.f1 >= req.f2:
        raise HTTPException(status_code=400, detail="f1 debe ser menor que f2")
    sweep, _ = generar_sine_sweep(req.f1, req.f2, req.duracion, req.fs)
    return _wav_response(sweep, req.fs, "sine_sweep.wav")


@router.post("/synthetic-ir", summary="Genera RI sintetica")
async def generar_ri_sintetica_endpoint(req: SyntheticIRRequest) -> StreamingResponse:
    """Genera una respuesta al impulso sintetica con T60 por banda y la devuelve como WAV."""
    try:
        t60_por_banda = {float(k): v for k, v in req.t60_por_banda.items()}
    except (ValueError, TypeError) as e:
        raise HTTPException(
            status_code=400,
            detail=f"Las claves de t60_por_banda deben ser frecuencias numericas: {e}",
        )
    ri = sintetizar_ri(t60_por_banda, req.fs, req.duracion)
    return _wav_response(ri, req.fs, "synthetic_ir.wav")
