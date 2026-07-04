"""Mide la respuesta al impulso de una sala usando sine sweep.

Genera un sine sweep, lo reproduce por los parlantes y graba la respuesta
por el micrófono. Guarda la grabación y el filtro inverso como archivos WAV
para procesarlos luego con obtener_ri_desde_sweep.

Ejecutar desde la raiz del proyecto:
    uv run python docs/m2/scripts/medir_ri.py

Los archivos se guardan en docs/m2/mediciones/.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import fftconvolve

ROOT_DIR = Path(__file__).parents[3]
sys.path.insert(0, str(ROOT_DIR))

from app.services.grabacion_utils import reproducir_y_grabar
from app.services.signal_utils import obtener_ri_desde_sweep
from app.services.sine_sweep import generar_sine_sweep

# =========================
# PARÁMETROS DE MEDICIÓN
# =========================
FS = 44100
F1 = 20
F2 = 20000
DURACION_SWEEP = 10.0
SILENCIO_POST = 3.0       # segundos extra para capturar la cola de reverb
DURACION_GRABACION = DURACION_SWEEP + SILENCIO_POST

# =========================
# CARPETA DE SALIDA
# =========================
out_dir = Path(__file__).parent.parent / "mediciones"
out_dir.mkdir(exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# =========================
# GENERACIÓN DEL SWEEP
# =========================
print(f"Generando sweep {F1} Hz → {F2} Hz, {DURACION_SWEEP} s...")
sweep, filtro_inverso = generar_sine_sweep(F1, F2, DURACION_SWEEP, FS)

# =========================
# MEDICIÓN
# =========================
print(f"Reproduciendo y grabando ({DURACION_GRABACION} s)...")
print("  ¡Silencio durante la medición!")

grabacion = reproducir_y_grabar(sweep, FS, DURACION_GRABACION)

print("Medición completada.")

# =========================
# PROCESAMIENTO — RIs
# =========================
print("Calculando convolución completa...")
ri_completa = fftconvolve(grabacion, filtro_inverso, mode="full")
ri_completa = ri_completa / np.max(np.abs(ri_completa)) * 0.9

print("Calculando RI con detección de onset...")
ri_procesada = obtener_ri_desde_sweep(grabacion, filtro_inverso)

# =========================
# GUARDADO
# =========================
path_grabacion = out_dir / f"grabacion_{timestamp}.wav"
path_filtro    = out_dir / f"filtro_inverso_{timestamp}.wav"
path_ri_full   = out_dir / f"ri_completa_{timestamp}.wav"
path_ri_proc   = out_dir / f"ri_procesada_{timestamp}.wav"

sf.write(str(path_grabacion), grabacion, FS)
sf.write(str(path_filtro),    filtro_inverso, FS)
sf.write(str(path_ri_full),   ri_completa.astype(np.float32), FS)
sf.write(str(path_ri_proc),   ri_procesada.astype(np.float32), FS)

print(f"Grabación guardada:         {path_grabacion}")
print(f"Filtro inverso guardado:    {path_filtro}")
print(f"RI completa (convolución):  {path_ri_full}")
print(f"RI procesada (con onset):   {path_ri_proc}")
