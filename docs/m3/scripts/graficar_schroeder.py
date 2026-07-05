"""Curva de Schroeder con rectas de ajuste T20 y T30 sobre la RI (Lundeby).

Genera 3 graficos separados (Elveden Hall, Maes Howe, RI medida), cada uno con:
  - la curva de decaimiento de Schroeder (EDC), truncada con el metodo de
    Lundeby, en rojo,
  - puntos sobre la curva en -5, -15, -25 y -35 dB, etiquetados con su nivel,
  - la recta de regresion T20 (rango -5 a -25 dB) punteada, en naranja,
  - la recta de regresion T30 (rango -5 a -35 dB) punteada, en azul,
    ambas dibujadas por debajo de la curva de Schroeder,
  - eje vertical con marcas cada 10 dB, hasta -100 dB.

Uso:
    uv run python docs/m3/scripts/graficar_schroeder.py
"""

import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import soundfile as sf
from matplotlib.ticker import MultipleLocator

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "../../.."))
sys.path.insert(0, ROOT_DIR)

from app.services.acoustic_parameters import (
    integral_schroeder,
    metodo_lundeby,
    regresion_lineal,
)
from app.services.signal_utils import cargar_audio

OUT_DIR = os.path.join(SCRIPT_DIR, "../Imagenes")
os.makedirs(OUT_DIR, exist_ok=True)

COLOR_EDC = "#e34948"
COLOR_T20 = "#eb6834"
COLOR_T30 = "#2a78d6"
COLOR_PUNTOS = "#0b0b0b"
COLOR_GRID = "#e1e0d9"

Y_BOTTOM = -100.0
NIVELES_PUNTOS = [-5.0, -15.0, -25.0, -35.0]


def cargar_mono(ruta: str) -> tuple[np.ndarray, int]:
    """Carga un WAV y lo devuelve en mono (promedio de canales si es necesario)."""
    ri, fs = cargar_audio(ruta)
    if ri.ndim > 1:
        ri = ri.mean(axis=1)
    return ri, fs


def tiempo_en_nivel(t: np.ndarray, edc: np.ndarray, nivel: float) -> float | None:
    """Interpola el instante en que la curva cruza `nivel` dB (curva decreciente)."""
    idx = np.argmax(edc <= nivel)
    if edc[idx] > nivel:
        return None
    if idx == 0:
        return float(t[0])
    e0, e1 = edc[idx - 1], edc[idx]
    t0, t1 = t[idx - 1], t[idx]
    frac = (nivel - e0) / (e1 - e0)
    return float(t0 + frac * (t1 - t0))


ri_elv, fs_elv = cargar_mono(os.path.join(ROOT_DIR, "docs/m2/elveden_hall/elveden_hall.wav"))
ri_mae, fs_mae = cargar_mono(os.path.join(ROOT_DIR, "docs/m2/maes_howe/maes_howe.wav"))

mediciones_dir = os.path.join(ROOT_DIR, "docs/m2/mediciones")
archivo_proc = sorted(
    [f for f in os.listdir(mediciones_dir) if f.startswith("ri_procesada_")], reverse=True
)[0]
ri_proc, fs_proc = sf.read(os.path.join(mediciones_dir, archivo_proc))
if ri_proc.ndim > 1:
    ri_proc = ri_proc.mean(axis=1)

ris = [
    ("Elveden Hall", ri_elv, fs_elv),
    ("Maes Howe", ri_mae, fs_mae),
    ("RI medida", ri_proc, fs_proc),
]

for nombre, ri, fs in ris:
    idx_trunc, _ = metodo_lundeby(ri, fs)
    ri_trunc = ri[:idx_trunc]

    edc = integral_schroeder(ri_trunc)
    t = np.arange(len(edc)) / fs

    # La integral de Schroeder cae abruptamente a -inf en las ultimas muestras
    # del array integrado, ya que ahi no queda energia remanente por sumar
    # (es un efecto de borde matematico, no un problema de la senal). Se
    # recorta el ultimo 1.5% de la curva truncada antes de graficar para no
    # mostrar esa caida artificial; no afecta el ajuste de T20/T30 porque ese
    # tramo esta muy por debajo de los -35 dB que usa la regresion.
    n_recorte = max(1, int(0.015 * len(edc)))
    edc = edc[:-n_recorte]
    t = t[:-n_recorte]

    mask_t20 = (edc <= -5.0) & (edc >= -25.0)
    pend20, ord20, _ = regresion_lineal(t[mask_t20], edc[mask_t20])

    mask_t30 = (edc <= -5.0) & (edc >= -35.0)
    pend30, ord30, _ = regresion_lineal(t[mask_t30], edc[mask_t30])

    xlim_right = t[-1]

    t_regr = np.linspace(0, xlim_right, 200)
    edc_regr_20 = pend20 * t_regr + ord20
    edc_regr_30 = pend30 * t_regr + ord30

    fig, ax = plt.subplots(figsize=(8, 6))

    ax.plot(t_regr, edc_regr_20, color=COLOR_T20, linewidth=1.8, linestyle="--",
             label="T20 (-5 a -25 dB)", zorder=1)
    ax.plot(t_regr, edc_regr_30, color=COLOR_T30, linewidth=1.8, linestyle="--",
             label="T30 (-5 a -35 dB)", zorder=1)

    ax.plot(t, edc, color=COLOR_EDC, linewidth=1.5, label="Curva de Schroeder", zorder=2)

    puntos_t = [tiempo_en_nivel(t, edc, nivel) for nivel in NIVELES_PUNTOS]
    puntos_validos = [(tp, nivel) for tp, nivel in zip(puntos_t, NIVELES_PUNTOS) if tp is not None]
    if puntos_validos:
        tx, ty = zip(*puntos_validos)
        ax.scatter(tx, ty, color=COLOR_PUNTOS, s=28, zorder=3)
        for tp, nivel in puntos_validos:
            ax.annotate(
                f"{nivel:.0f} dB", xy=(tp, nivel), xytext=(6, 0),
                textcoords="offset points", ha="left", va="center",
                fontsize=9, color=COLOR_PUNTOS, zorder=4,
            )

    ax.set_xlim(0, xlim_right)
    ax.set_ylim(Y_BOTTOM, 5)
    ax.yaxis.set_major_locator(MultipleLocator(10))
    ax.set_xlabel("Tiempo [s]")
    ax.set_ylabel("Nivel [dB]")
    ax.set_title(f"Curva de Schroeder - {nombre}")
    ax.grid(color=COLOR_GRID, linewidth=1)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.legend(fontsize=9, frameon=False, loc="upper right")

    plt.tight_layout()

    slug = nombre.lower().replace(" ", "_")
    out = os.path.join(OUT_DIR, f"schroeder_lundeby_t30_{slug}.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("Guardado:", out)
