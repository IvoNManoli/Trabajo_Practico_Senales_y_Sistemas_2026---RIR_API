"""Servicio de convolucion de audio con respuesta al impulso."""

from math import gcd

import numpy as np
from scipy.signal import fftconvolve, resample_poly


def convolucionar(audio: np.ndarray, ri: np.ndarray, fs_audio: int, fs_ri: int) -> np.ndarray:
    """Convoluciona un audio seco con una respuesta al impulso.

    Si los archivos tienen distinta frecuencia de muestreo, la RI se
    resamplea al fs del audio antes de convolucionar.

    Parameters
    ----------
    audio : np.ndarray
        Senal de audio seca (1D, mono).
    ri : np.ndarray
        Respuesta al impulso (1D).
    fs_audio : int
        Frecuencia de muestreo del audio en Hz.
    fs_ri : int
        Frecuencia de muestreo de la RI en Hz.

    Returns
    -------
    np.ndarray
        Audio convolucionado, normalizado a 0.9, misma fs que el audio entrada.
    """
    if fs_ri != fs_audio:
        divisor = gcd(fs_audio, fs_ri)
        ri = resample_poly(ri, fs_audio // divisor, fs_ri // divisor)

    resultado = fftconvolve(audio, ri, mode="full")

    pico = np.max(np.abs(resultado))
    if pico > 0:
        resultado = resultado / pico * 0.9

    return resultado.astype(np.float32)
