"""Genera los graficos de validacion del Milestone 1.

Ejecutar desde la raiz del proyecto:
    uv run python docs/m1/generar_graficos.py

Genera tres PNGs en docs/m1/:
    - ruido_rosa_espectro.png
    - sweep_espectrograma.png
    - convolucion_impulso.png
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import fftconvolve, welch

# Asegurar imports del proyecto
import sys
sys.path.insert(0, str(Path(__file__).parents[2]))

from app.services.pink_noise import generar_ruido_rosa
from app.services.sine_sweep import generar_sine_sweep

OUTPUT_DIR = Path(__file__).parent
FS = 44100


# ── Grafico 1: Espectro del ruido rosa ──────────────────────────────────────

def grafico_ruido_rosa():
    print("Generando grafico de ruido rosa...")
    ruido = generar_ruido_rosa(duracion=10.0, fs=FS)

    frecuencias, psd = welch(ruido, fs=FS, nperseg=4096)

    # Filtrar banda de interes
    mascara = (frecuencias >= 20) & (frecuencias <= 20000)
    f = frecuencias[mascara]
    p = psd[mascara]

    # Referencia teorica -3 dB/oct (PSD ∝ 1/f)
    p_teorica = p[0] * (f[0] / f)

    # Pendiente medida en dB/oct
    log_f = np.log2(f)
    log_p_db = 10 * np.log10(p)
    pendiente_db_oct, _ = np.polyfit(log_f, log_p_db, 1)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.semilogx(f, 10 * np.log10(p), color="steelblue", alpha=0.6, lw=1, label="PSD medida (Welch)")
    ax.semilogx(f, 10 * np.log10(p_teorica), color="tomato", lw=2, linestyle="--",
                label="Teorico -3 dB/oct")
    ax.set_xlabel("Frecuencia (Hz)")
    ax.set_ylabel("PSD (dB/Hz)")
    ax.set_title(f"Espectro del ruido rosa — pendiente medida: {pendiente_db_oct:.2f} dB/oct")
    ax.legend()
    ax.grid(True, which="both", alpha=0.3)
    ax.set_xlim(20, 20000)

    path = OUTPUT_DIR / "ruido_rosa_espectro.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Guardado: {path}")


# ── Grafico 2: Espectrograma del sine sweep ──────────────────────────────────

def grafico_sweep():
    print("Generando espectrograma del sweep...")
    sweep, _ = generar_sine_sweep(f1=20, f2=20000, duracion=5.0, fs=FS)

    fig, axes = plt.subplots(2, 1, figsize=(10, 7), gridspec_kw={"height_ratios": [1, 2]})

    # Forma de onda
    t = np.linspace(0, 5.0, len(sweep))
    axes[0].plot(t, sweep, lw=0.5, color="steelblue")
    axes[0].set_ylabel("Amplitud")
    axes[0].set_xlim(0, 5.0)
    axes[0].set_title("Sine sweep logaritmico 20 Hz → 20 kHz, 5 s")

    # Espectrograma
    axes[1].specgram(sweep, Fs=FS, NFFT=1024, noverlap=512,
                     cmap="inferno", scale="dB")
    axes[1].set_yscale("log")
    axes[1].set_ylim(20, FS / 2)
    axes[1].set_xlabel("Tiempo (s)")
    axes[1].set_ylabel("Frecuencia (Hz)")
    axes[1].set_xlim(0, 5.0)

    fig.tight_layout()
    path = OUTPUT_DIR / "sweep_espectrograma.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Guardado: {path}")


# ── Grafico 3: Convolucion sweep × filtro inverso ────────────────────────────

def grafico_convolucion():
    print("Generando grafico de convolucion sweep x filtro inverso...")
    sweep, filtro_inverso = generar_sine_sweep(f1=20, f2=20000, duracion=5.0, fs=FS)
    resultado = fftconvolve(sweep, filtro_inverso)

    indice_pico = np.argmax(np.abs(resultado))
    valor_pico = np.abs(resultado[indice_pico])
    mascara = np.ones(len(resultado), dtype=bool)
    mascara[max(0, indice_pico - 100):indice_pico + 100] = False
    piso = np.mean(np.abs(resultado[mascara]))
    snr_db = 20 * np.log10(valor_pico / piso)

    # Tiempo relativo al pico
    t_total = np.arange(len(resultado)) / FS
    t_relativo = (np.arange(len(resultado)) - indice_pico) / FS * 1000  # ms

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    # Vista completa
    axes[0].plot(t_total, resultado, lw=0.5, color="steelblue")
    axes[0].axvline(indice_pico / FS, color="tomato", lw=1.5, linestyle="--",
                    label=f"Pico en t={indice_pico/FS:.2f} s")
    axes[0].set_xlabel("Tiempo (s)")
    axes[0].set_ylabel("Amplitud (normalizada)")
    axes[0].set_title(f"sweep × filtro_inverso — SNR pico/piso ≈ {snr_db:.1f} dB")
    axes[0].legend()

    # Zoom ±5 ms alrededor del pico
    ventana_ms = 5
    mascara_zoom = np.abs(t_relativo) <= ventana_ms
    axes[1].plot(t_relativo[mascara_zoom], resultado[mascara_zoom],
                 lw=1.2, color="steelblue")
    axes[1].axvline(0, color="tomato", lw=1.5, linestyle="--")
    axes[1].set_xlabel("Tiempo respecto al pico (ms)")
    axes[1].set_ylabel("Amplitud (normalizada)")
    axes[1].set_title("Zoom ±5 ms: aproximacion al impulso δ(t)")

    fig.tight_layout()
    path = OUTPUT_DIR / "convolucion_impulso.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Guardado: {path}")


if __name__ == "__main__":
    grafico_ruido_rosa()
    grafico_sweep()
    grafico_convolucion()
    print("\nListo. Los 3 graficos estan en docs/m1/")
