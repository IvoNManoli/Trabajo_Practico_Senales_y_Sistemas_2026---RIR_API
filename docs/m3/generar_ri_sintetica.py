"""Script para generar respuestas al impulso sinteticas.

Genera RIs con distintos T60 por banda y las guarda como WAV en docs/m3/.

Uso:
    uv run python docs/m3/generar_ri_sintetica.py
"""

import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.services.signal_utils import sintetizar_ri  # noqa: E402

SALIDA = Path(__file__).parent
FS = 44100


def guardar(ri: np.ndarray, nombre: str) -> None:
    ruta = SALIDA / nombre
    sf.write(ruta, ri, FS, format="WAV", subtype="PCM_16")
    print(f"Guardado: {ruta}  ({len(ri)/FS:.1f} s, {FS} Hz)")


if __name__ == "__main__":
    np.random.seed(0)

    # RI con T60 uniforme de 1.5 s en todas las bandas
    ri_1 = sintetizar_ri(
        {125: 1.5, 250: 1.5, 500: 1.5, 1000: 1.5, 2000: 1.5, 4000: 1.5},
        fs=FS,
        duracion=4.0,
    )
    guardar(ri_1, "ri_sintetica_t60_1.5s.wav")

    # RI con T60 variable por banda (sala grande tipica)
    ri_2 = sintetizar_ri(
        {125: 2.5, 250: 2.2, 500: 1.9, 1000: 1.7, 2000: 1.5, 4000: 1.2},
        fs=FS,
        duracion=5.0,
    )
    guardar(ri_2, "ri_sintetica_sala_grande.wav")

    # RI anecóica (T60 muy corto, para prueba de D50 alto)
    ri_3 = sintetizar_ri(
        {125: 0.3, 250: 0.3, 500: 0.3, 1000: 0.3, 2000: 0.3, 4000: 0.3},
        fs=FS,
        duracion=1.5,
    )
    guardar(ri_3, "ri_sintetica_t60_0.3s.wav")
