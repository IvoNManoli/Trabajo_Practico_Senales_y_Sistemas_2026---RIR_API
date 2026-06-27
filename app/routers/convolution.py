"""Router para convolucion de audio con respuesta al impulso.

Endpoints:
    POST /with-ir           → convoluciona audio subido con RI subida
    POST /with-synthetic-ir → convoluciona audio subido con RI sintetica
"""

import io

import numpy as np
import soundfile as sf
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.services.convolution import convolucionar
from app.services.signal_utils import cargar_audio, sintetizar_ri

router = APIRouter()


def _wav_response(signal: np.ndarray, fs: int, filename: str) -> StreamingResponse:
    buf = io.BytesIO()
    sf.write(buf, signal, fs, format="WAV", subtype="PCM_16")
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="audio/wav",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/with-ir", summary="Convoluciona audio con una RI subida")
async def convolucionar_con_ri(
    audio: UploadFile = File(..., description="Audio seco en formato WAV"),  # noqa: B008
    ri: UploadFile = File(..., description="Respuesta al impulso en formato WAV"),  # noqa: B008
) -> StreamingResponse:
    """Aplica reverberacion a un audio seco convolucionandolo con una RI medida o sintetizada."""
    try:
        audio_data, fs_audio = cargar_audio(io.BytesIO(audio.file.read()))
        ri_data, fs_ri = cargar_audio(io.BytesIO(ri.file.read()))
    except Exception as e:
        raise HTTPException(
            status_code=422, detail=f"No se pudo leer el archivo de audio: {e}"
        ) from e

    resultado = convolucionar(audio_data, ri_data, fs_audio, fs_ri)
    return _wav_response(resultado, fs_audio, "audio_convolucionado.wav")


@router.post("/with-synthetic-ir", summary="Convoluciona audio con una RI sintetica")
async def convolucionar_con_ri_sintetica(
    audio: UploadFile = File(..., description="Audio seco en formato WAV"),  # noqa: B008
    t60_125: float = Form(default=2.0, description="T60 en 125 Hz (s)"),  # noqa: B008
    t60_250: float = Form(default=2.0, description="T60 en 250 Hz (s)"),  # noqa: B008
    t60_500: float = Form(default=2.0, description="T60 en 500 Hz (s)"),  # noqa: B008
    t60_1000: float = Form(default=2.0, description="T60 en 1000 Hz (s)"),  # noqa: B008
    t60_2000: float = Form(default=2.0, description="T60 en 2000 Hz (s)"),  # noqa: B008
    t60_4000: float = Form(default=2.0, description="T60 en 4000 Hz (s)"),  # noqa: B008
    t60_8000: float = Form(default=2.0, description="T60 en 8000 Hz (s)"),  # noqa: B008
    t60_16000: float = Form(default=2.0, description="T60 en 16000 Hz (s)"),  # noqa: B008
    duracion: float = Form(default=3.0, description="Duracion de la RI en segundos"),  # noqa: B008
) -> StreamingResponse:
    """Genera una RI sintetica con los T60 indicados por banda y la convoluciona con el audio."""
    t60_dict = {
        125.0: t60_125,
        250.0: t60_250,
        500.0: t60_500,
        1000.0: t60_1000,
        2000.0: t60_2000,
        4000.0: t60_4000,
        8000.0: t60_8000,
        16000.0: t60_16000,
    }

    try:
        audio_data, fs_audio = cargar_audio(io.BytesIO(audio.file.read()))
    except Exception as e:
        raise HTTPException(
            status_code=422, detail=f"No se pudo leer el archivo de audio: {e}"
        ) from e

    ri_data = sintetizar_ri(t60_dict, fs_audio, duracion)
    resultado = convolucionar(audio_data, ri_data, fs_audio, fs_audio)
    return _wav_response(resultado, fs_audio, "audio_con_reverb_sintetica.wav")
