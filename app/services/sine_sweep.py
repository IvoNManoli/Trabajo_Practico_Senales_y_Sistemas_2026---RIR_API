"""Servicio de generacion de sine sweep logaritmico.

Milestone 1: Generacion de senales.
"""

import numpy as np


def generar_sine_sweep(
    f1: float, f2: float, duracion: float, fs: int
) -> tuple[np.ndarray, np.ndarray]:
    """Genera un barrido senoidal logaritmico (sine sweep) y su filtro inverso.

    El sine sweep logaritmico es la senal de excitacion preferida para
    la medicion de respuestas al impulso segun la tecnica de Farina (2000).

    Parameters
    ----------
    f1 : float
        Frecuencia inicial del barrido en Hz (tipicamente 20 Hz).
    f2 : float
        Frecuencia final del barrido en Hz (tipicamente 20000 Hz).
    duracion : float
        Duracion del barrido en segundos.
    fs : int
        Frecuencia de muestreo en Hz.

    Returns
    -------
    sweep : np.ndarray
        Senal del barrido senoidal.
    filtro_inverso : np.ndarray
        Filtro inverso correspondiente.

    References
    ----------
    .. [1] Farina, A. (2000). "Simultaneous measurement of impulse response
       and distortion with a swept-sine technique."
    """

    n_muestras = int(duracion * fs)
    tiempo = np.linspace(0, duracion, n_muestras, endpoint=False)
    l_constante = duracion / np.log(f2 / f1)
    fase = 2 * np.pi * f1 * l_constante * (np.exp(tiempo / l_constante) - 1)
    sweep = np.sin(fase)
    sweep_invertido = sweep[::-1]
    rampa = np.exp(-tiempo / l_constante)
    filtro_inverso = sweep_invertido * rampa
    filtro_inverso = filtro_inverso / np.max(np.abs(filtro_inverso))
    # Aplico una reducción de ganancia de -6 dB para no estar tan cerca de clipear
    ganancia_headroom = 0.5
    sweep = sweep * ganancia_headroom
    filtro_inverso = filtro_inverso * ganancia_headroom

    return sweep, filtro_inverso
