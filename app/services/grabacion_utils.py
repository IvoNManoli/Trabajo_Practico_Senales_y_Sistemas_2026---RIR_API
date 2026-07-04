"""Utilidades de grabacion y reproduccion de audio.

Milestone 1: Generacion de senales.
"""

import numpy as np
import sounddevice as sd


def reproducir_y_grabar(
    signal: np.ndarray,
    fs: int,
    duracion_grabacion: float,
    preroll: float = 0.5,
) -> np.ndarray:
    """Reproduce una senal y graba simultaneamente el audio del recinto.

    Parameters
    ----------
    signal : np.ndarray
        Senal de excitacion a reproducir (1D mono o 2D estereo).
    fs : int
        Frecuencia de muestreo en Hz.
    duracion_grabacion : float
        Duracion de la grabacion en segundos. Debe ser mayor que la duracion
        de la senal para capturar la cola de reverberacion.
    preroll : float, optional
        Silencio inicial en segundos antes de la senal para compensar la
        latencia del sistema de audio. Por defecto 0.5 s.

    Returns
    -------
    np.ndarray
        Senal grabada como array 1D (incluye el preroll al inicio). La
        grabacion siempre es mono (1 microfono), independientemente de si
        la senal reproducida es mono o estereo.

    Raises
    ------
    RuntimeError
        Si no hay dispositivo de audio disponible.
    """
    n_preroll = int(preroll * fs)
    n_grabacion = int(duracion_grabacion * fs) + n_preroll
    n_senal = signal.shape[0]
    n_padding = max(0, n_grabacion - n_senal - n_preroll)

    if signal.ndim == 1:
        senal_extendida = np.concatenate([
            np.zeros(n_preroll),
            signal,
            np.zeros(n_padding),
        ])
    else:
        n_channels_salida = signal.shape[1]
        senal_extendida = np.vstack([
            np.zeros((n_preroll, n_channels_salida)),
            signal,
            np.zeros((n_padding, n_channels_salida)),
        ])

    try:
        datos_capturados = sd.playrec(
            senal_extendida,
            samplerate=fs,
            channels=1,
            blocking=True,
        )
        sd.wait()
        return datos_capturados.ravel()
    except sd.PortAudioError as e:
        raise RuntimeError(f"No hay dispositivo de audio disponible: {e}") from e
