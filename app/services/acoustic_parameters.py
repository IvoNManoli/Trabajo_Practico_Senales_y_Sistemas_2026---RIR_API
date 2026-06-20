"""Servicio de calculo de parametros acusticos segun ISO 3382.

Milestone 3: Analisis de parametros acusticos.
"""

import numpy as np
from scipy.signal import hilbert

_BANDAS: list[float] = [125.0, 250.0, 500.0, 1000.0, 2000.0, 4000.0]
_EPS = np.finfo(float).eps


def suavizar_signal(signal: np.ndarray, ventana: int | str = "hilbert") -> np.ndarray:
    """Suaviza una senal para reducir fluctuaciones del ruido.

    Parameters
    ----------
    signal : np.ndarray
        Senal de entrada (tipicamente una RI filtrada por banda).
    ventana : int | str
        Si es 'hilbert': envolvente instantanea via scipy.signal.hilbert.
        Si es int: media movil de la energia con esa ventana en muestras.

    Returns
    -------
    np.ndarray
        Senal suavizada (envolvente de energia), misma longitud que signal.
    """
    if isinstance(ventana, str):
        analitica = hilbert(signal)
        return np.abs(analitica)
    n = int(ventana)
    kernel = np.ones(n) / n
    return np.convolve(signal**2, kernel, mode="same")


def integral_schroeder(ri: np.ndarray) -> np.ndarray:
    """Calcula la integral de Schroeder (Energy Decay Curve).

    Integracion inversa de la energia: sum de h^2[k] desde n hasta N,
    normalizada a 0 dB en el primer valor.

    Parameters
    ----------
    ri : np.ndarray
        Respuesta al impulso (array 1D).

    Returns
    -------
    np.ndarray
        Curva de decaimiento de Schroeder en dB, normalizada a 0 dB.

    References
    ----------
    .. [1] Schroeder, M. R. (1965). "New method of measuring reverberation
       time." Journal of the Acoustical Society of America, 37(3), 409-412.
    """
    energia = ri**2
    integral = np.cumsum(energia[::-1])[::-1]
    return 10.0 * np.log10(integral / integral[0] + _EPS)


def regresion_lineal(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    """Calcula la regresion lineal por minimos cuadrados.

    Implementacion manual de minimos cuadrados para demostrar comprension
    del metodo. La pendiente en dB/s permite calcular T60 = -60 / pendiente.

    Parameters
    ----------
    x : np.ndarray
        Variable independiente (tipicamente tiempo en segundos).
    y : np.ndarray
        Variable dependiente (tipicamente curva de Schroeder en dB).

    Returns
    -------
    tuple[float, float, float]
        (pendiente, ordenada_al_origen, r_cuadrado)
        pendiente en dB/s, ordenada en dB, coeficiente de determinacion R^2.
    """
    n = len(x)
    sum_x = np.sum(x)
    sum_y = np.sum(y)
    sum_xy = np.sum(x * y)
    sum_x2 = np.sum(x**2)

    denom = n * sum_x2 - sum_x**2
    if denom == 0:
        return 0.0, float(np.mean(y)), 0.0

    pendiente = (n * sum_xy - sum_x * sum_y) / denom
    ordenada = (sum_y - pendiente * sum_x) / n

    y_pred = pendiente * x + ordenada
    ss_res = float(np.sum((y - y_pred) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0

    return float(pendiente), float(ordenada), r2


def _calcular_tiempo(
    edc: np.ndarray, t: np.ndarray, limite_sup: float, limite_inf: float,
    r2_minimo: float = 0.9,
) -> float | None:
    """Calcula el tiempo de reverberacion extrapolando la pendiente de la EDC a -60 dB.

    Retorna None si hay menos de 2 puntos en el rango, la pendiente es positiva
    (piso de ruido) o el ajuste lineal es pobre (R^2 < r2_minimo).
    """
    mask = (edc <= limite_sup) & (edc >= limite_inf)
    if np.sum(mask) < 2:
        return None
    pendiente, _, r2 = regresion_lineal(t[mask], edc[mask])
    if pendiente >= 0 or r2 < r2_minimo:
        return None
    return float(-60.0 / pendiente)


def calcular_parametros_acusticos(
    ri: np.ndarray, fs: int
) -> dict[str, dict[float, float | None]]:
    """Calcula los parametros acusticos ISO 3382 por banda de octava.

    Calcula EDT, T10, T20, T30, D50 y C80 para las bandas de octava
    125, 250, 500, 1000, 2000 y 4000 Hz.

    Parameters
    ----------
    ri : np.ndarray
        Respuesta al impulso (array 1D).
    fs : int
        Frecuencia de muestreo en Hz.

    Returns
    -------
    dict[str, dict[float, float | None]]
        Diccionario con parametros acusticos por banda.
        Estructura: {'EDT': {125.0: val, 250.0: val, ...}, 'T30': {...}, ...}

    References
    ----------
    .. [1] ISO 3382-1:2009. "Acoustics -- Measurement of room acoustic
       parameters -- Part 1: Performance spaces."
    """
    from app.services.filter import filtro_octava

    if ri.ndim > 1:
        ri = ri[:, 0]

    resultado: dict[str, dict[float, float | None]] = {
        "EDT": {},
        "T10": {},
        "T20": {},
        "T30": {},
        "D50": {},
        "C80": {},
    }

    n_50ms = int(0.05 * fs)
    n_80ms = int(0.08 * fs)

    for fc in _BANDAS:
        ri_banda = filtro_octava(ri, fc=fc, fs=fs)
        edc = integral_schroeder(ri_banda)
        t = np.arange(len(ri_banda)) / fs
        energia = ri_banda**2

        resultado["EDT"][fc] = _calcular_tiempo(edc, t, 0.0, -10.0)
        resultado["T10"][fc] = _calcular_tiempo(edc, t, -5.0, -15.0)
        resultado["T20"][fc] = _calcular_tiempo(edc, t, -5.0, -25.0)
        resultado["T30"][fc] = _calcular_tiempo(edc, t, -5.0, -35.0)

        energia_total = float(np.sum(energia))
        if energia_total > 0 and n_50ms < len(ri_banda):
            resultado["D50"][fc] = float(np.sum(energia[:n_50ms]) / energia_total * 100.0)
        else:
            resultado["D50"][fc] = None

        if n_80ms < len(ri_banda):
            e_temprana = float(np.sum(energia[:n_80ms]))
            e_tardia = float(np.sum(energia[n_80ms:]))
            if e_tardia > 0:
                resultado["C80"][fc] = float(10.0 * np.log10(e_temprana / e_tardia))
            else:
                resultado["C80"][fc] = None
        else:
            resultado["C80"][fc] = None

    return resultado


def metodo_lundeby(ri: np.ndarray, fs: int) -> tuple[int, float]:
    """Determina el punto de truncamiento de la RI usando el metodo de Lundeby.

    Parameters
    ----------
    ri : np.ndarray
        Respuesta al impulso (array 1D).
    fs : int
        Frecuencia de muestreo en Hz.

    Returns
    -------
    tuple[int, float]
        (indice_truncamiento, nivel_ruido_dB)

    Notes
    -----
    Esta funcion es opcional (extra credit en M3).

    References
    ----------
    .. [1] Lundeby, A. et al. (1995). "Uncertainties of measurements in
       room acoustics." Acustica, 81(4), 344-355.
    """
    raise NotImplementedError("Implementar en Milestone 3 (opcional)")
