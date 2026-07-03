"""Prueba de envolvente de Hilbert por banda de octava sobre Elveden Hall."""

import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import soundfile as sf

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "../.."))
sys.path.insert(0, ROOT_DIR)

from app.services.acoustic_parameters import suavizar_signal
from app.services.filter import filtro_octava
from app.services.signal_utils import cargar_audio

BANDAS = [500, 4000, 16000]

path_elv = os.path.join(SCRIPT_DIR, "elveden_hall", "elveden_hall.wav")
ri, fs = cargar_audio(path_elv)
if ri.ndim > 1:
    ri = ri.mean(axis=1)

for fc in BANDAS:
    ri_banda = filtro_octava(ri, fc=float(fc), fs=fs)
    env = suavizar_signal(ri_banda, "hilbert")
    t = np.arange(len(env)) / fs

    plt.figure(figsize=(18, 7))
    plt.plot(t, env, linewidth=0.8)
    plt.title(f"Elveden Hall — Envolvente de Hilbert {fc} Hz")
    plt.xlabel("Tiempo [s]")
    plt.ylabel("Amplitud")
    plt.xlim(0, 4)
    plt.grid(alpha=0.3)
    plt.tight_layout()

    out = os.path.join(SCRIPT_DIR, "imagenes", f"hilbert_{fc}hz.png")
    plt.savefig(out, dpi=150)
    plt.close()
    print("Guardado:", out)

# RI procesada en 4 kHz
mediciones_dir = os.path.join(SCRIPT_DIR, "mediciones")
archivos_proc = sorted(
    [f for f in os.listdir(mediciones_dir) if f.startswith("ri_procesada_")],
    reverse=True,
)
ri_proc, fs_proc = sf.read(os.path.join(mediciones_dir, archivos_proc[0]))
if ri_proc.ndim > 1:
    ri_proc = ri_proc.mean(axis=1)

ri_proc_banda = filtro_octava(ri_proc, fc=4000.0, fs=fs_proc)
env_proc = suavizar_signal(ri_proc_banda, "hilbert")
t_proc = np.arange(len(env_proc)) / fs_proc

plt.figure(figsize=(14, 5))
plt.plot(t_proc, env_proc, linewidth=0.8)
plt.title("RI medida — Envolvente de Hilbert 4000 Hz")
plt.xlabel("Tiempo [s]")
plt.ylabel("Amplitud")
plt.xlim(0, 0.4)
plt.grid(alpha=0.3)
plt.tight_layout()

out = os.path.join(SCRIPT_DIR, "imagenes", "hilbert_procesada_4000hz.png")
plt.savefig(out, dpi=150)
plt.close()
print("Guardado:", out)
