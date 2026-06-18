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

import soundfile as sf

from app.services.signal_utils import a_escala_log, cargar_audio, sintetizar_ri

BANDAS = [125, 250, 500, 1000, 2000, 4000]
FS_REF = 44100

# =========================
# CARPETAS OUTPUT
# =========================
out_elv = os.path.join(SCRIPT_DIR, "elveden_hall")
out_mae = os.path.join(SCRIPT_DIR, "maes_howe")
out_img = os.path.join(SCRIPT_DIR, "imagenes")

os.makedirs(out_elv, exist_ok=True)
os.makedirs(out_mae, exist_ok=True)
os.makedirs(out_img, exist_ok=True)


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

out_file = os.path.join(out_img, "elveden_hall_ir.png")
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

out_file = os.path.join(out_img, "maes_howe_ir.png")
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

out_file = os.path.join(out_img, "respuesta_filtros.png")
plt.savefig(out_file, dpi=150)
plt.close()
print("OK Guardado:", out_file)


# =========================
# RI MEDIDA — completa y procesada
# =========================
mediciones_dir = os.path.join(SCRIPT_DIR, "mediciones")

archivos_full = sorted(
    [f for f in os.listdir(mediciones_dir) if f.startswith("ri_completa_")],
    reverse=True,
)
archivos_proc = sorted(
    [f for f in os.listdir(mediciones_dir) if f.startswith("ri_procesada_")],
    reverse=True,
)

if not archivos_full or not archivos_proc:
    print("No se encontraron archivos de medición en mediciones/. Saltando plots de RI medida.")
else:
    ri_full, fs_med = sf.read(os.path.join(mediciones_dir, archivos_full[0]))
    ri_proc, _     = sf.read(os.path.join(mediciones_dir, archivos_proc[0]))

    # RI completa: recortar desde 100 ms antes del pico
    MARGEN_MS = 100
    margen_muestras = int(MARGEN_MS / 1000 * fs_med)
    idx_pico = int(np.argmax(np.abs(ri_full)))
    idx_inicio = max(0, idx_pico - margen_muestras)
    ri_full_recortada = ri_full[idx_inicio:]
    # t=0 en el pico, margen visible como tiempo negativo
    t_full_ms = (np.arange(len(ri_full_recortada)) - margen_muestras) / fs_med * 1000

    plt.figure(figsize=(10, 4))
    plt.plot(t_full_ms, ri_full_recortada, linewidth=0.5, color="steelblue")
    plt.xlabel("Tiempo [ms]")
    plt.ylabel("Amplitud")
    plt.title("RI medida — Convolución completa")
    plt.xlim(-MARGEN_MS, 250 - MARGEN_MS)
    plt.grid(alpha=0.3)
    plt.tight_layout()
    out_file = os.path.join(out_img, "ri_medida_completa.png")
    plt.savefig(out_file, dpi=150)
    plt.close()
    print("OK Guardado:", out_file)

    # RI completa — igual pero con línea vertical en el onset de ri_procesada
    idx_pico_proc = int(np.argmax(np.abs(ri_proc)))
    t_onset_ms = -idx_pico_proc / fs_med * 1000

    plt.figure(figsize=(10, 4))
    plt.plot(t_full_ms, ri_full_recortada, linewidth=0.5, color="steelblue")
    plt.axvline(t_onset_ms, color="tomato", linestyle="--", linewidth=1.5,
                label=f"Valor inicial de RI aplicando criterio ≈ {-round(t_onset_ms)} ms antes del pico")
    plt.xlabel("Tiempo [ms]")
    plt.ylabel("Amplitud")
    plt.title("RI medida — Convolución completa y umbral temporal ")
    plt.xlim(-MARGEN_MS, 250 - MARGEN_MS)
    plt.legend(loc="upper right")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    out_file = os.path.join(out_img, "ri_medida_completa_onset.png")
    plt.savefig(out_file, dpi=150)
    plt.close()
    print("OK Guardado:", out_file)

    # RI completa — duración total señalando el último 10% usado para estimar el piso de ruido
    n_ruido = max(1, len(ri_full) // 10)
    t_all_ms = (np.arange(len(ri_full)) - idx_pico) / fs_med * 1000
    t_noise_start_ms = float((len(ri_full) - n_ruido - idx_pico) / fs_med * 1000)
    t_noise_end_ms   = float((len(ri_full) - idx_pico) / fs_med * 1000)

    fig, ax = plt.subplots(figsize=(13, 4))
    ax.plot(t_all_ms, ri_full, linewidth=0.3, color="steelblue")
    ax.axvspan(t_noise_start_ms, t_noise_end_ms, alpha=0.15, color="tomato", zorder=0)

    ylim = ax.get_ylim()
    y_span = ylim[1] - ylim[0]
    x_text = t_noise_end_ms / 2   # centro del eje x completo
    y_text = ylim[0] + y_span * 0.82   # desplazado hacia arriba

    ax.annotate(
        f"Último 10% de la señal:\nEstimación RMS del piso de ruido\npara el umbral",
        xy=(t_noise_start_ms + (t_noise_end_ms - t_noise_start_ms) * 0.3, 0),
        xytext=(x_text, y_text),
        fontsize=14,
        color="tomato",
        ha="center",
        va="center",
        bbox=dict(facecolor="white", edgecolor="tomato", alpha=0.85, boxstyle="round,pad=0.4"),
        arrowprops=dict(arrowstyle="->", color="tomato", lw=1.5),
    )

    ax.set_xlim(-MARGEN_MS, t_noise_end_ms + MARGEN_MS)
    ax.set_xlabel("Tiempo [ms]")
    ax.set_ylabel("Amplitud")
    ax.set_title("Estimación del piso de ruido en la convolución completa")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    out_file = os.path.join(out_img, "ri_medida_piso_ruido.png")
    fig.savefig(out_file, dpi=150)
    plt.close(fig)
    print("OK Guardado:", out_file)

    # RI procesada — t=0 en el onset (ya recortada por obtener_ri_desde_sweep)
    t_proc_ms = np.arange(len(ri_proc)) / fs_med * 1000

    plt.figure(figsize=(10, 4))
    plt.plot(t_proc_ms, ri_proc, linewidth=0.5, color="steelblue")
    plt.xlabel("Tiempo [ms]")
    plt.ylabel("Amplitud")
    plt.title("RI de obtener_ri_desde_sweep()")
    plt.xlim(0, 250)
    plt.grid(alpha=0.3)
    plt.tight_layout()
    out_file = os.path.join(out_img, "ri_medida_procesada.png")
    plt.savefig(out_file, dpi=150)
    plt.close()
    print("OK Guardado:", out_file)

print("M2 COMPLETADO")

