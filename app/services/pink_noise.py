"""Servicio de generacion de ruido rosa.

Milestone 1: Generacion de senales.
"""

import numpy as np

def generar_ruido_rosa(duracion: float, fs: int) -> np.ndarray:
    """Genera una senal de ruido rosa de la duracion especificada.

    El ruido rosa tiene una densidad espectral de potencia inversamente
    proporcional a la frecuencia (1/f). Esto significa que cada octava
    contiene la misma cantidad de energia, lo cual lo hace util para
    mediciones acusticas.

    Algoritmo sugerido:
    1. Generar ruido blanco (distribucion normal) de la duracion deseada.
    2. Aplicar la transformada de Fourier (np.fft.rfft).
    3. Crear un vector de frecuencias correspondiente.
    4. Dividir cada componente por sqrt(f) (omitir f=0 para evitar division por cero).
    5. Aplicar la transformada inversa (np.fft.irfft).
    6. Normalizar la senal resultante al rango [-1, 1].

    Parameters
    ----------
    duracion : float
        Duracion de la senal en segundos.
    fs : int
        Frecuencia de muestreo en Hz.

    Returns
    -------
    np.ndarray
        Senal de ruido rosa normalizada, de longitud ``int(duracion * fs)``.
    """
    n_muestras = int(duracion * fs)
    # Generar ruido blanco (distribucion normal) de la duracion deseada.
    ruido_blanco = np.random.randn(n_muestras)
    # Normalizar para que el pico sea 0.8
    ruido_blanco = ruido_blanco / np.max(np.abs(ruido_blanco)) * 0.8
    # Aplicar la transformada de Fourier (np.fft.rfft).
    ruido_fft = np.fft.rfft(ruido_blanco)
    # Vector de frecuencias
    frecuencias = np.fft.rfftfreq(n_muestras, d=1 / fs)
    # Dividir cada componente por sqrt(f) (omitir f=0 para evitar division por cero).
    factores = np.ones_like(frecuencias)
    factores[1:] = 1.0 / np.sqrt(frecuencias[1:])
    espectro_rosa_fft = (ruido_fft * factores)  # Filtro para generar el ruido rosa (cuanta mayor es la frecuencia menor es la energía)
    # Aplicar la transformada inversa (np.fft.irfft)
    ruido_rosa = np.fft.irfft(espectro_rosa_fft, n=n_muestras)  # Pasando de frecuencial a temporal
    # Normalizar la señal resultante al rango [-1, 1].
    ruido_rosa_normalizado = ruido_rosa / np.max(np.abs(ruido_rosa)) * 0.8
    return ruido_rosa_normalizado

