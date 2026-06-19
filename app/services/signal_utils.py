"""Utilidades de procesamiento de senales.

Milestone 2: Procesamiento de la respuesta al impulso.
"""

from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import fftconvolve


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
    if np.max(np.abs(audio)) > 0:
        audio = audio / np.max(np.abs(audio)) * 0.9
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
    grabacion: np.ndarray, filtro_inverso: np.ndarray, margen_db: float = 20.0
) -> np.ndarray:
    """Obtiene la respuesta al impulso mediante deconvolucion de un sine sweep.

    Convoluciona la grabacion con el filtro inverso del sweep en el dominio
    frecuencial. Dado que grabacion = sweep * h, y sweep * filtro_inverso ≈ delta,
    el resultado es aproximadamente h (la RI del recinto).

    El inicio de la RI se determina retrocediendo desde el pico hasta el primer
    sample donde la senal supera el ruido de fondo en ``margen_db`` dB. Esto
    preserva el ataque de la envolvente del sonido directo.

    Parameters
    ----------
    grabacion : np.ndarray
        Senal grabada que contiene la respuesta de la sala al sweep.
    filtro_inverso : np.ndarray
        Filtro inverso del sweep utilizado en la excitacion.
    margen_db : float, optional
        Margen en dB sobre el RMS del ruido de fondo para determinar el inicio
        de la RI (por defecto 20 dB).

    Returns
    -------
    np.ndarray
        Respuesta al impulso estimada, normalizada, recortada desde el onset.
    """
    ri_full = fftconvolve(grabacion, filtro_inverso, mode="full")
    abs_ri = np.abs(ri_full)

    # Estimar RMS del ruido de fondo con el ultimo 10% de la senal
    n_ruido = max(1, len(ri_full) // 10)
    rms_ruido = np.sqrt(np.mean(ri_full[-n_ruido:] ** 2))
    umbral = rms_ruido * (10 ** (margen_db / 20.0))

    # Retroceder desde el pico hasta el onset (primera muestra sobre el umbral)
    idx_pico = int(np.argmax(abs_ri))
    idx_inicio = idx_pico
    while idx_inicio > 0 and abs_ri[idx_inicio - 1] >= umbral:
        idx_inicio -= 1

    ri = ri_full[idx_inicio:]
    return ri / np.max(np.abs(ri)) * 0.9


def a_escala_log(signal: np.ndarray) -> np.ndarray:
    """Convierte una senal a escala logaritmica (dB) normalizada.

    Calcula:

        L(t) = 20 * log10( |h(t)| / max(|h|) )

    El resultado tiene maximo en 0 dB y piso en -120 dB.

    Parameters
    ----------
    signal : np.ndarray
        Senal de entrada (array 1D).

    Returns
    -------
    np.ndarray
        Senal en decibeles normalizada a 0 dB en el maximo.
        Piso de ruido en -120 dB.
    """
    max_abs = np.max(np.abs(signal))
    if max_abs == 0:
        return np.full(len(signal), -120.0)
    ratio = np.abs(signal) / max_abs
    # Piso antes del log para evitar log(0)
    ratio = np.maximum(ratio, 10 ** (-120 / 20))
    return 20.0 * np.log10(ratio)
