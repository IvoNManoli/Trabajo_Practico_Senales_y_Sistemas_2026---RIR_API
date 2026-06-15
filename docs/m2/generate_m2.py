import os
import sys

import matplotlib.pyplot as plt
import numpy as np

# =========================
# FIX PATH (ROOT DEL PROYECTO)
# =========================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "../.."))
sys.path.insert(0, ROOT_DIR)

print("🔥 SCRIPT EJECUTÁNDOSE")
print("SCRIPT DIR:", SCRIPT_DIR)
print("ROOT DIR:", ROOT_DIR)

# =========================
# IMPORTS DEL PROYECTO
# =========================
from app.services.signal_utils import cargar_audio

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

print("🔊 Cargando IRs...")

ri_e, fs_e = cargar_audio(path_elv)
print("✔ Elveden OK:", ri_e.shape, fs_e)

ri_m, fs_m = cargar_audio(path_mae)
print("✔ Maes Howe OK:", ri_m.shape, fs_m)


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

print("✔ Guardado:", out_file)


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

print("✔ Guardado:", out_file)


print("🎉 M2 COMPLETADO")
