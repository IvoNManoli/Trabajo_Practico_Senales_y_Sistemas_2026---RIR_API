"""Router para generacion de senales (M1 + M3).

Endpoints:
    POST /pink-noise       → WAV de ruido rosa
    POST /sine-sweep       → WAV de sine sweep logaritmico
    POST /synthetic-ir     → WAV de RI sintetica con T60 por banda
"""

import io
import zipfile

import soundfile as sf
from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.signals import PinkNoiseRequest, SineSweepRequest
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


@router.post("/sine-sweep-pair", summary="Genera sine sweep y su filtro inverso")
async def generar_sine_sweep_par(req: SineSweepRequest) -> StreamingResponse:
    """Genera el sine sweep y el filtro inverso y los devuelve como ZIP con dos WAVs."""
    if req.f1 >= req.f2:
        raise HTTPException(status_code=400, detail="f1 debe ser menor que f2")
    sweep, filtro_inverso = generar_sine_sweep(req.f1, req.f2, req.duracion, req.fs)

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for nombre, senal in [("sine_sweep.wav", sweep), ("filtro_inverso.wav", filtro_inverso)]:
            wav_buf = io.BytesIO()
            sf.write(wav_buf, senal, req.fs, format="WAV", subtype="PCM_16")
            zf.writestr(nombre, wav_buf.getvalue())
    zip_buf.seek(0)
    return StreamingResponse(
        zip_buf,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="sine_sweep_par.zip"'},
    )


@router.post("/synthetic-ir", summary="Genera RI sintetica")
async def generar_ri_sintetica_endpoint(
    t60_125: float = Form(default=2.0, description="T60 en 125 Hz (s)"),  # noqa: B008
    t60_250: float = Form(default=2.0, description="T60 en 250 Hz (s)"),  # noqa: B008
    t60_500: float = Form(default=2.0, description="T60 en 500 Hz (s)"),  # noqa: B008
    t60_1000: float = Form(default=2.0, description="T60 en 1000 Hz (s)"),  # noqa: B008
    t60_2000: float = Form(default=2.0, description="T60 en 2000 Hz (s)"),  # noqa: B008
    t60_4000: float = Form(default=2.0, description="T60 en 4000 Hz (s)"),  # noqa: B008
    t60_8000: float = Form(default=2.0, description="T60 en 8000 Hz (s)"),  # noqa: B008
    t60_16000: float = Form(default=2.0, description="T60 en 16000 Hz (s)"),  # noqa: B008
    fs: int = Form(default=44100, description="Frecuencia de muestreo en Hz"),  # noqa: B008
    duracion: float = Form(default=3.0, description="Duracion de la RI en segundos"),  # noqa: B008
) -> StreamingResponse:
    """Genera una respuesta al impulso sintetica con T60 por banda y la devuelve como WAV."""
    t60_por_banda = {
        125.0: t60_125, 250.0: t60_250, 500.0: t60_500, 1000.0: t60_1000,
        2000.0: t60_2000, 4000.0: t60_4000, 8000.0: t60_8000, 16000.0: t60_16000,
    }
    ri = sintetizar_ri(t60_por_banda, fs, duracion)
    return _wav_response(ri, fs, "synthetic_ir.wav")
