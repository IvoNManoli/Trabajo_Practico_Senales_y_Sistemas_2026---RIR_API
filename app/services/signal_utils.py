"""Utilidades de procesamiento de senales.

Milestone 2: Procesamiento de la respuesta al impulso.
"""

from pathlib import Path

import numpy as np
import soundfile as sf


def cargar_audio(ruta: str | Path) -> tuple[np.ndarray, int]:
    """Carga un archivo de audio y retorna la senal y la frecuencia de muestreo.

    Parameters
    ----------
    ruta : str | Path
        Ruta al archivo de audio a cargar. Soporta WAV y FLAC.

    Returns
    -------
    signal : np.ndarray
        Senal de audio como float64 normalizada entre -1 y 1.
        Si el audio es estereo, shape es (n_muestras, n_canales).
    fs : int
        Frecuencia de muestreo del archivo en Hz.

    Raises
    ------
    FileNotFoundError
        Si el archivo especificado no existe.
    ValueError
        Si el formato no es soportado o el archivo no puede leerse.
    """
    ruta = Path(ruta)
    if not ruta.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {ruta}")
    try:
        audio, fs = sf.read(str(ruta), dtype="float64", always_2d=False)
    except Exception as exc:
        raise ValueError(f"No se pudo leer el archivo: {ruta}") from exc
    return audio, int(fs)


def sintetizar_ri(
    t60_por_banda: dict[float, float], fs: int, duracion: float
) -> np.ndarray:
    """Sintetiza una respuesta al impulso artificial a partir de valores T60 por banda.

    Modela la RI como ruido blanco filtrado en cada banda de octava multiplicado
    por una envolvente exponencial con decaimiento segun el T60 especificado:

        h(t) = sum_banda [ filtro_octava(ruido(t)) * exp(-alpha * t) ]

    donde alpha = 6.908 / T60 se deriva de la definicion de T60 como el tiempo
    en que la energia decae 60 dB.

    Parameters
    ----------
    t60_por_banda : dict[float, float]
        Diccionario {frecuencia_central_Hz: T60_segundos}.
        Ejemplo: {125: 2.0, 500: 1.5, 1000: 1.2, 4000: 0.8}
    fs : int
        Frecuencia de muestreo en Hz.
    duracion : float
        Duracion de la respuesta al impulso en segundos.

    Returns
    -------
    np.ndarray
        Respuesta al impulso sintetizada (array 1D), normalizada.
    """
    from app.services.filter import filtro_octava

    n = int(duracion * fs)
    t = np.arange(n) / fs
    ri = np.zeros(n)
    for fc, t60 in t60_por_banda.items():
        alpha = 6.908 / t60
        ruido = np.random.randn(n)
        banda = filtro_octava(ruido, fc=float(fc), fs=fs)
        ri += banda * np.exp(-alpha * t)
    max_val = np.max(np.abs(ri))
    if max_val > 0:
        ri = ri / max_val * 0.9
    return ri


def obtener_ri_desde_sweep(
    grabacion: np.ndarray, filtro_inverso: np.ndarray
) -> np.ndarray:
    """Obtiene la respuesta al impulso mediante deconvolucion de un sine sweep.

    Parameters
    ----------
    grabacion : np.ndarray
        Senal grabada que contiene la respuesta de la sala al sweep.
    filtro_inverso : np.ndarray
        Filtro inverso del sweep utilizado.

    Returns
    -------
    np.ndarray
        Respuesta al impulso estimada, normalizada.
    """
    raise NotImplementedError("Implementar en Milestone 2")


def a_escala_log(signal: np.ndarray) -> np.ndarray:
    """Convierte una senal a escala logaritmica (dB) normalizada.

    Parameters
    ----------
    signal : np.ndarray
        Senal de entrada (array 1D).

    Returns
    -------
    np.ndarray
        Senal en escala logaritmica (dB), normalizada a 0 dB en el maximo.
    """
    raise NotImplementedError("Implementar en Milestone 2")
