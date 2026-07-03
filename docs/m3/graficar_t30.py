"""Graficos de T20 y T30 por banda de octava para Elveden Hall, Maes Howe y RI medida."""

import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import soundfile as sf

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "../.."))
sys.path.insert(0, ROOT_DIR)

from app.services.acoustic_parameters import calcular_parametros_acusticos
from app.services.signal_utils import cargar_audio

BANDAS = [125, 250, 500, 1000, 2000, 4000]
OUT_DIR = os.path.join(SCRIPT_DIR, "imagenes")
os.makedirs(OUT_DIR, exist_ok=True)

# Carga de RIs
ri_elv, fs_elv = cargar_audio(os.path.join(ROOT_DIR, "docs/m2/elveden_hall/elveden_hall.wav"))
if ri_elv.ndim > 1:
    ri_elv = ri_elv.mean(axis=1)

ri_mae, fs_mae = cargar_audio(os.path.join(ROOT_DIR, "docs/m2/maes_howe/maes_howe.wav"))
if ri_mae.ndim > 1:
    ri_mae = ri_mae.mean(axis=1)

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

x = np.arange(len(BANDAS))
etiquetas = [str(fc) for fc in BANDAS]

for nombre, ri, fs in ris:
    params = calcular_parametros_acusticos(ri, fs)

    edt = [params["EDT"].get(float(fc)) for fc in BANDAS]
    t10 = [params["T10"].get(float(fc)) for fc in BANDAS]
    t20 = [params["T20"].get(float(fc)) for fc in BANDAS]
    t30 = [params["T30"].get(float(fc)) for fc in BANDAS]

    fig, ax = plt.subplots(figsize=(16, 7))

    ax.plot(x, edt, marker="^", linestyle=":", label="EDT", color="#003f8a")
    ax.plot(x, t10, marker="D", linestyle="-.", label="T10", color="#f5c400")
    ax.plot(x, t20, marker="o", linestyle="--", label="T20", color="#f07800")
    ax.plot(x, t30, marker="s", linestyle="-", label="T30", color="#c0000c")

    ax.set_xticks(x)
    ax.set_xticklabels(etiquetas)
    ax.set_xlabel("Frecuencia central de banda [Hz]")
    ax.set_ylabel("Tiempo de reverberación [s]")
    ax.set_title(f"{nombre} — Tiempos de reverberación por banda de octava")
    ax.legend()
    ax.grid(alpha=0.3)
    plt.tight_layout()

    nombre_archivo = nombre.lower().replace(" ", "_")
    out = os.path.join(OUT_DIR, f"t30_{nombre_archivo}.png")
    plt.savefig(out, dpi=150)
    plt.close()
    print("Guardado:", out)

# Comparativa RI medida: con vs sin Lundeby
params_con = calcular_parametros_acusticos(ri_proc, fs_proc, usar_lundeby=True)
params_sin = calcular_parametros_acusticos(ri_proc, fs_proc, usar_lundeby=False)

fig, axes = plt.subplots(1, 2, figsize=(20, 7), sharey=True)

for ax, params, titulo in [
    (axes[0], params_con, "RI medida — Con Lundeby"),
    (axes[1], params_sin, "RI medida — Sin Lundeby"),
]:
    edt = [params["EDT"].get(float(fc)) for fc in BANDAS]
    t10 = [params["T10"].get(float(fc)) for fc in BANDAS]
    t20 = [params["T20"].get(float(fc)) for fc in BANDAS]
    t30 = [params["T30"].get(float(fc)) for fc in BANDAS]

    ax.plot(x, edt, marker="^", linestyle=":", label="EDT", color="#003f8a")
    ax.plot(x, t10, marker="D", linestyle="-.", label="T10", color="#f5c400")
    ax.plot(x, t20, marker="o", linestyle="--", label="T20", color="#f07800")
    ax.plot(x, t30, marker="s", linestyle="-", label="T30", color="#c0000c")

    ax.set_xticks(x)
    ax.set_xticklabels(etiquetas)
    ax.set_xlabel("Frecuencia central de banda [Hz]")
    ax.set_ylabel("Tiempo de reverberación [s]")
    ax.set_title(titulo)
    ax.legend()
    ax.grid(alpha=0.3)

plt.tight_layout()
out = os.path.join(OUT_DIR, "t30_ri_medida_comparativa_lundeby.png")
plt.savefig(out, dpi=150)
plt.close()
print("Guardado:", out)
