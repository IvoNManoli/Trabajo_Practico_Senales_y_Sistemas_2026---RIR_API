"""Utilidades de grabacion y reproduccion de audio.

Milestone 1: Generacion de senales.
"""

import numpy as np
import sounddevice as sd


def reproducir_y_grabar(
    signal: np.ndarray,
    fs: int,
    duracion_grabacion: float
) -> np.ndarray:
    """Reproduce una senal y graba simultaneamente el audio del recinto.

    Parameters
    ----------
    signal : np.ndarray
        Senal de excitacion a reproducir (1D o 2D).
    fs : int
        Frecuencia de muestreo en Hz.
    duracion_grabacion : float
        Duracion de la grabacion en segundos. Debe ser mayor que la duracion
        de la senal para capturar la cola de reverberacion.

    Returns
    -------
    np.ndarray
        Senal grabada como array 1D.

    Raises
    ------
    RuntimeError
        Si no hay dispositivo de audio disponible.
    """
    n_grabacion = int(duracion_grabacion * fs)
    n_senal = signal.shape[0]
    n_padding = max(0, n_grabacion - n_senal)

    if signal.ndim == 1:
        senal_extendida = np.concatenate([signal, np.zeros(n_padding)])
    else:
        senal_extendida = np.vstack([signal, np.zeros((n_padding, signal.shape[1]))])

    try:
        datos_capturados = sd.playrec(
            senal_extendida,
            samplerate=fs,
            channels=1,
            blocking=True
        )
        sd.wait()
        return datos_capturados.ravel()
    except sd.PortAudioError as e:
        raise RuntimeError(f"No hay dispositivo de audio disponible: {e}") from e

