import numpy as np
import sounddevice as sd

def reproducir_y_grabar(
    senal_excitacion: np.ndarray, 
    fs: int, 
    num_canales: int = 1
) -> np.ndarray:
    """
    Reproduce una señal de audio y captura simultáneamente el audio del recinto a través 
    del micrófono

    Parameters
    ----------
    senal_excitacion : np.ndarray
        Vector o matriz que contiene las muestras del estímulo a reproducir.
    fs : int
        Frecuencia de muestreo del sistema en Hertz (ej: 44100).
    num_canales : int, opcional
        Cantidad de canales de entrada a registrar (1 para Mono, 2 para Estéreo).
        Por defecto se establece en 1.

    Returns
    -------
    np.ndarray
        Array con las muestras de la señal grabada. Si el registro es mono, 
        se retorna como un vector unidimensional (1D).
    """
    # 1. Ejecución síncrona de I/O de audio mediante la placa de sonido.
    # El parámetro blocking=True detiene la ejecución del script de Python
    # hasta que se hayan reproducido y grabado la totalidad de las muestras.
    datos_capturados = sd.playrec(
        senal_excitacion,
        samplerate=fs,
        channels=num_canales,
        blocking=True
    )
    
    # 2. Post-procesamiento dimensional:
    # Sounddevice por defecto retorna matrices bidimensionales (muestras x canales).
    # Si la captura es monofónica, se aplana el array para trabajar con un vector 
    # de una única dimensión, facilitando los cálculos posteriores de convolución.
    if num_canales == 1:
        datos_capturados = datos_capturados.ravel()
        
    return datos_capturados