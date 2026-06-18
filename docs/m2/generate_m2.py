import os
import sys

import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import butter, sosfreqz

# =========================
# FIX PATH (ROOT DEL PROYECTO)
# =========================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "../.."))
sys.path.insert(0, ROOT_DIR)

from app.services.signal_utils import a_escala_log, cargar_audio, sintetizar_ri

BANDAS = [125, 250, 500, 1000, 2000, 4000]
FS_REF = 44100

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
# PLOT ELVEDEN — IR
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


# =========================
# PLOT MAES HOWE — IR
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


# =========================
# RESPUESTA EN FRECUENCIA — filtro_octava (IEC 61260)
# =========================
fig, ax = plt.subplots(figsize=(10, 5))

for fc in BANDAS:
    f_inf = fc / np.sqrt(2)
    f_sup = fc * np.sqrt(2)
    w_inf = 2 * f_inf / FS_REF
    w_sup = 2 * f_sup / FS_REF
    sos = butter(4, [w_inf, w_sup], btype="band", output="sos")
    w, h = sosfreqz(sos, worN=8192, fs=FS_REF)
    mag_db = 20 * np.log10(np.maximum(np.abs(h), 1e-10))
    ax.semilogx(w, mag_db, label=f"{fc} Hz")
    ax.axvline(f_inf, color="gray", linestyle=":", linewidth=0.6, alpha=0.5)
    ax.axvline(f_sup, color="gray", linestyle=":", linewidth=0.6, alpha=0.5)

ax.axhline(-3, color="black", linestyle="--", linewidth=0.8, label="-3 dB")
ax.set_xlim(50, 12000)
ax.set_ylim(-80, 5)
ax.set_xlabel("Frecuencia [Hz]")
ax.set_ylabel("Ganancia [dB]")
ax.set_title("Respuesta en frecuencia — filtros de banda de octava (IEC 61260, orden 4)")
ax.legend(loc="lower right")
ax.grid(True, which="both", alpha=0.3)
plt.tight_layout()

out_file = os.path.join(SCRIPT_DIR, "respuesta_filtros.png")
plt.savefig(out_file, dpi=150)
plt.close()
print("OK Guardado:", out_file)


# =========================
# RI SINTETIZADA — mismo T60 en todas las bandas
# =========================
T60 = 1.5
duracion = 3.0
t60_por_banda = {fc: T60 for fc in BANDAS}

ri_sint = sintetizar_ri(t60_por_banda, fs=FS_REF, duracion=duracion)
t_sint = np.arange(len(ri_sint)) / FS_REF

plt.figure(figsize=(10, 4))
plt.plot(t_sint, a_escala_log(ri_sint), color="steelblue", linewidth=0.8)
plt.axhline(-60, color="red", linestyle="--", linewidth=0.8, label="-60 dB")
plt.xlabel("Tiempo [s]")
plt.ylabel("Amplitud [dB]")
plt.title(f"RI sintetizada — T60 = {T60} s en todas las bandas")
plt.ylim(-120, 5)
plt.legend()
plt.grid(alpha=0.4)
plt.tight_layout()

out_file = os.path.join(SCRIPT_DIR, "ri_sintetizada.png")
plt.savefig(out_file, dpi=150)
plt.close()
print("OK Guardado:", out_file)

print("M2 COMPLETADO")
