"""Servicio de calculo de parametros acusticos segun ISO 3382.

Milestone 3: Analisis de parametros acusticos.
"""

import numpy as np
from scipy.signal import hilbert

_BANDAS: list[float] = [125.0, 250.0, 500.0, 1000.0, 2000.0, 4000.0, 8000.0, 16000.0]
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
    if integral[0] == 0:
        return np.full(len(ri), -np.inf)
    return 10.0 * np.log10(np.maximum(integral / integral[0], _EPS))


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
    edc: np.ndarray,
    t: np.ndarray,
    limite_sup: float,
    limite_inf: float,
    r2_minimo: float = 0.8,
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
    ri: np.ndarray, fs: int, usar_lundeby: bool = True
) -> dict[str, dict[float, float | None]]:
    """Calcula los parametros acusticos ISO 3382 por banda de octava.

    Calcula EDT, T10, T20, T30, D50 y C80 para las bandas de octava
    125, 250, 500, 1000, 2000, 4000, 8000 y 16000 Hz.

    Parameters
    ----------
    ri : np.ndarray
        Respuesta al impulso (array 1D).
    fs : int
        Frecuencia de muestreo en Hz.
    usar_lundeby : bool, optional
        Si True, aplica el metodo de Lundeby para truncar la RI antes de
        calcular la integral de Schroeder. Util para RIs medidas con ruido
        de fondo real. Por defecto True.

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
        "SNR": {},
    }

    n_50ms = int(0.05 * fs)
    n_80ms = int(0.08 * fs)

    for fc in _BANDAS:
        ri_banda = filtro_octava(ri, fc=fc, fs=fs)
        energia = ri_banda**2

        if usar_lundeby:
            idx_trunc, nivel_ruido_db = metodo_lundeby(ri_banda, fs)
            ri_para_edc = ri_banda[:idx_trunc]
        else:
            n_ruido = max(1, len(ri_banda) // 10)
            nivel_ruido_db = 10.0 * np.log10(np.mean(ri_banda[-n_ruido:] ** 2) + _EPS)
            ri_para_edc = ri_banda

        pico_db = 10.0 * np.log10(np.max(ri_banda**2) + _EPS)
        resultado["SNR"][fc] = round(pico_db - nivel_ruido_db, 1)

        edc = integral_schroeder(ri_para_edc)
        t = np.arange(len(ri_para_edc)) / fs

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

    Busca iterativamente el punto donde la curva de decaimiento de la RI
    se cruza con el piso de ruido de fondo. Permite definir limites de
    integracion precisos para corregir la integral de Schroeder.

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
        Indice de la muestra donde la RI se cruza con el ruido de fondo
        y el nivel estimado de ruido en dB.

    References
    ----------
    .. [1] Lundeby, A. et al. (1995). "Uncertainties of measurements in
       room acoustics." Acustica, 81(4), 344-355.
    """
    n_int = max(1, int(0.01 * fs))  # ~10 ms por intervalo
    n_intervals = len(ri) // n_int

    if n_intervals < 10:
        return len(ri) - 1, float(10.0 * np.log10(np.mean(ri**2) + _EPS))

    # Energia media de la RI en intervalos de 10 ms
    bloques = ri[: n_intervals * n_int].reshape(n_intervals, n_int)
    energia_int = np.mean(bloques**2, axis=1)
    t_int = (np.arange(n_intervals) + 0.5) * n_int / fs

    # Estimacion inicial del ruido: promedio del ultimo 10% de intervalos
    n_ruido_int = max(1, n_intervals // 10)
    nivel_ruido = float(np.mean(energia_int[-n_ruido_int:]))

    idx_trunc_int = n_intervals - 1

    for _ in range(15):
        nivel_ruido_db = 10.0 * np.log10(max(nivel_ruido, _EPS))
        energia_db = 10.0 * np.log10(np.maximum(energia_int, _EPS))

        # Cruce preliminar: primer intervalo con energia <= piso de ruido + 10 dB
        cruces = np.where(energia_db <= nivel_ruido_db + 10.0)[0]
        idx_cruce = int(cruces[0]) if len(cruces) > 0 else n_intervals - 1
        if idx_cruce < 2:
            break

        # Regresion lineal desde el inicio hasta el cruce preliminar
        pendiente, ordenada, _ = regresion_lineal(t_int[:idx_cruce], energia_db[:idx_cruce])
        if pendiente >= 0:
            break

        # Muestra donde la recta de regresion cruza el piso de ruido
        t_trunc = (nivel_ruido_db - ordenada) / pendiente
        nuevo_idx = int(np.clip(round(t_trunc * fs / n_int), 1, n_intervals - 1))

        # Reestimar el piso de ruido con los intervalos tras el truncamiento
        if nuevo_idx < n_intervals - 1:
            nueva_est = float(np.mean(energia_int[nuevo_idx:]))
            if nueva_est > 0:
                nivel_ruido = nueva_est

        if abs(nuevo_idx - idx_trunc_int) <= 1:
            idx_trunc_int = nuevo_idx
            break
        idx_trunc_int = nuevo_idx

    idx_sample = int(np.clip(idx_trunc_int * n_int, 0, len(ri) - 1))
    return idx_sample, float(10.0 * np.log10(max(nivel_ruido, _EPS)))
