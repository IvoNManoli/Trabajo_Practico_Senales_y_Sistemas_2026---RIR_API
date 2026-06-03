"""Servicio de filtrado por bandas de octava.

Milestone 2: Procesamiento de la respuesta al impulso.
"""

import numpy as np
from scipy.signal import butter, filtfilt


def filtro_octava(
    signal: np.ndarray, fc: float, fs: int, orden: int = 4
) -> np.ndarray:
    """Aplica un filtro pasabanda de una octava centrado en ``fc``.

    Frecuencias de corte segun IEC 61260:

        f_inf = fc / sqrt(2)
        f_sup = fc * sqrt(2)

    Usa ``filtfilt`` (fase cero) para evitar distorsion de fase, lo cual es
    critico para el calculo correcto de parametros temporales como EDT y T60.

    Parameters
    ----------
    signal : np.ndarray
        Senal de entrada (array 1D).
    fc : float
        Frecuencia central de la banda de octava en Hz.
    fs : int
        Frecuencia de muestreo en Hz.
    orden : int, optional
        Orden del filtro Butterworth (por defecto 4).

    Returns
    -------
    np.ndarray
        Senal filtrada (array 1D).
    """
    f_inf = fc / np.sqrt(2)
    f_sup = fc * np.sqrt(2)
    nyq = fs / 2.0
    # f_sup puede superar Nyquist en bandas altas (ej. 16 kHz a 44.1 kHz fs)
    wn = [f_inf / nyq, min(f_sup / nyq, 0.9999)]
    b, a = butter(orden, wn, btype="band")
    return filtfilt(b, a, signal)
