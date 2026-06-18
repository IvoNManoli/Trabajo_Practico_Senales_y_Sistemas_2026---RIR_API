import os
import sys

import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import hilbert

# =========================
# FIX PATH (ROOT DEL PROYECTO)
# =========================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "../.."))
sys.path.insert(0, ROOT_DIR)

print("SCRIPT EJECUTANDOSE")
print("SCRIPT DIR:", SCRIPT_DIR)
print("ROOT DIR:", ROOT_DIR)

# =========================
# IMPORTS DEL PROYECTO
# =========================
from app.services.filter import filtro_octava
from app.services.signal_utils import a_escala_log, cargar_audio

BANDAS = [125, 250, 500, 1000, 2000, 4000]

# =========================
# CARPETAS OUTPUT
# =========================
out_elv = os.path.join(SCRIPT_DIR, "elveden_hall")
out_mae = os.path.join(SCRIPT_DIR, "maes_howe")

os.makedirs(out_elv, exist_ok=True)
os.makedirs(out_mae, exist_ok=True)


# =========================
# CARGA DE IRs
# =========================
path_elv = os.path.join(out_elv, "elveden_hall.wav")
path_mae = os.path.join(out_mae, "maes_howe.wav")

print("Cargando IRs...")

ri_e, fs_e = cargar_audio(path_elv)
if ri_e.ndim > 1:
    ri_e = ri_e.mean(axis=1)
print("OK Elveden OK:", ri_e.shape, fs_e)

ri_m, fs_m = cargar_audio(path_mae)
if ri_m.ndim > 1:
    ri_m = ri_m.mean(axis=1)
print("OK Maes Howe OK:", ri_m.shape, fs_m)


# =========================
# PLOT ELVEDEN
# =========================
t_e = np.arange(len(ri_e)) / fs_e

plt.figure(figsize=(10, 4))
plt.plot(t_e, ri_e)
plt.title("Elveden Hall - IR")
plt.xlabel("Tiempo [s]")
plt.ylabel("Amplitud")
plt.grid()

out_file = os.path.join(out_elv, "ir.png")
plt.savefig(out_file, dpi=150)
plt.close()
print("OK Guardado:", out_file)

# Decaimiento logaritmico
plt.figure(figsize=(10, 4))
plt.plot(t_e, a_escala_log(np.abs(hilbert(ri_e))))
plt.title("Elveden Hall - Decaimiento logaritmico")
plt.xlabel("Tiempo [s]")
plt.ylabel("Amplitud [dB]")
plt.ylim(-120, 5)
plt.axhline(-60, color="red", linestyle="--", linewidth=0.8, label="-60 dB")
plt.legend()
plt.grid()
out_file = os.path.join(out_elv, "decaimiento_log.png")
plt.savefig(out_file, dpi=150)
plt.close()
print("OK Guardado:", out_file)

# Decaimiento por banda de octava
plt.figure(figsize=(10, 5))
for fc in BANDAS:
    banda = filtro_octava(ri_e, fc=float(fc), fs=fs_e)
    plt.plot(t_e, a_escala_log(np.abs(hilbert(banda))), label=f"{fc} Hz")
plt.title("Elveden Hall - Decaimiento por banda de octava")
plt.xlabel("Tiempo [s]")
plt.ylabel("Amplitud [dB]")
plt.ylim(-120, 5)
plt.axhline(-60, color="black", linestyle="--", linewidth=0.8, label="-60 dB")
plt.legend(loc="upper right")
plt.grid()
out_file = os.path.join(out_elv, "decaimiento_por_banda.png")
plt.savefig(out_file, dpi=150)
plt.close()
print("OK Guardado:", out_file)


# =========================
# PLOT MAES HOWE
# =========================
t_m = np.arange(len(ri_m)) / fs_m

plt.figure(figsize=(10, 4))
plt.plot(t_m, ri_m)
plt.title("Maes Howe - IR")
plt.xlabel("Tiempo [s]")
plt.ylabel("Amplitud")
plt.grid()

out_file = os.path.join(out_mae, "ir.png")
plt.savefig(out_file, dpi=150)
plt.close()
print("OK Guardado:", out_file)

# Decaimiento logaritmico
plt.figure(figsize=(10, 4))
plt.plot(t_m, a_escala_log(np.abs(hilbert(ri_m))))
plt.title("Maes Howe - Decaimiento logaritmico")
plt.xlabel("Tiempo [s]")
plt.ylabel("Amplitud [dB]")
plt.ylim(-120, 5)
plt.axhline(-60, color="red", linestyle="--", linewidth=0.8, label="-60 dB")
plt.legend()
plt.grid()
out_file = os.path.join(out_mae, "decaimiento_log.png")
plt.savefig(out_file, dpi=150)
plt.close()
print("OK Guardado:", out_file)

# Decaimiento por banda de octava
plt.figure(figsize=(10, 5))
for fc in BANDAS:
    banda = filtro_octava(ri_m, fc=float(fc), fs=fs_m)
    plt.plot(t_m, a_escala_log(np.abs(hilbert(banda))), label=f"{fc} Hz")
plt.title("Maes Howe - Decaimiento por banda de octava")
plt.xlabel("Tiempo [s]")
plt.ylabel("Amplitud [dB]")
plt.ylim(-120, 5)
plt.axhline(-60, color="black", linestyle="--", linewidth=0.8, label="-60 dB")
plt.legend(loc="upper right")
plt.grid()
out_file = os.path.join(out_mae, "decaimiento_por_banda.png")
plt.savefig(out_file, dpi=150)
plt.close()
print("OK Guardado:", out_file)


print("M2 COMPLETADO")
