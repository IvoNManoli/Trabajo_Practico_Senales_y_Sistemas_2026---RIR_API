"""Genera los graficos de validacion del Milestone 1.

Ejecutar desde la raiz del proyecto:
    uv run python docs/m1/generar_graficos.py

Genera tres PNGs en docs/m1/:
    - ruido_rosa_espectro.png
    - sweep_forma_onda.png
    - convolucion_impulso.png

Los espectrogramas (ruido rosa y sweep) fueron generados externamente
con Audacity y se encuentran en la misma carpeta como archivos PNG separados.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FixedFormatter, FixedLocator
from scipy.signal import fftconvolve, welch

# Asegurar imports del proyecto
import sys
sys.path.insert(0, str(Path(__file__).parents[2]))

from app.services.pink_noise import generar_ruido_rosa
from app.services.sine_sweep import generar_sine_sweep

OUTPUT_DIR = Path(__file__).parent / "imagenes"
OUTPUT_DIR.mkdir(exist_ok=True)
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

    fc_octava  = [31.5, 63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
    fc_tercios = [20, 25, 31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315,
                  400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500, 3150, 4000,
                  5000, 6300, 8000, 10000, 12500, 16000, 20000]

    fig, ax = plt.subplots(figsize=(12, 8))
    ax.semilogx(f, 10 * np.log10(p), color="steelblue", alpha=0.6, lw=1, label="PSD medida (Welch)")
    ax.semilogx(f, 10 * np.log10(p_teorica), color="tomato", lw=2, linestyle="--",
                label="Teorico -3 dB/oct")
    ax.set_xlabel("Frecuencia (Hz)")
    ax.set_ylabel("PSD (dB/Hz)")
    ax.set_title(f"Espectro del ruido rosa — pendiente medida: {pendiente_db_oct:.2f} dB/oct")
    ax.legend()
    ax.set_xlim(20, 20000)

    fc_oct_labels = [str(int(fc)) if fc == int(fc) else str(fc) for fc in fc_octava]
    ax.xaxis.set_major_locator(FixedLocator(fc_octava))
    ax.xaxis.set_major_formatter(FixedFormatter(fc_oct_labels))
    ax.tick_params(axis='x', which='major', labelsize=9)

    ax.xaxis.set_minor_locator(FixedLocator(fc_tercios))
    ax.tick_params(axis='x', which='minor', labelbottom=False, length=3)

    # Ticks en Y anclados al valor exacto a 1000 Hz, saltos de 3 dB
    idx_1k = np.argmin(np.abs(f - 1000))
    val_1k = 10 * np.log10(p[idx_1k])
    p_db = 10 * np.log10(p)
    n_down = int(np.ceil((val_1k - (p_db.min() - 3)) / 3)) + 1
    n_up   = int(np.ceil(((p_db.max() + 3) - val_1k) / 3)) + 1
    ticks_y = [val_1k + n * 3 for n in range(-n_down, n_up + 1)]
    ax.yaxis.set_major_locator(FixedLocator(ticks_y))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.1f}"))

    ax.grid(True, which='major', alpha=0.5, linewidth=0.8)
    ax.grid(True, which='minor', alpha=0.25, linewidth=0.5)

    path = OUTPUT_DIR / "ruido_rosa_espectro.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Guardado: {path}")


# ── Grafico 2: Forma de onda del sine sweep ──────────────────────────────────

def grafico_sweep():
    print("Generando forma de onda del sweep...")
    sweep, _ = generar_sine_sweep(f1=20, f2=20000, duracion=5.0, fs=FS)

    t = np.linspace(0, 5.0, len(sweep))

    fig, ax = plt.subplots(figsize=(10, 3))
    ax.plot(t, sweep, lw=0.4, color="steelblue")
    ax.set_xlabel("Tiempo (s)")
    ax.set_ylabel("Amplitud")
    ax.set_xlim(0, 5.0)
    ax.set_title("Forma de onda — sine sweep logaritmico 20 Hz → 20 kHz, 5 s")
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    path = OUTPUT_DIR / "sweep_forma_onda.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Guardado: {path}")


# ── Grafico 3: Convolucion sweep × filtro inverso ────────────────────────────

def grafico_convolucion():
    print("Generando grafico de convolucion Sweep * Filtro inverso...")
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

    # Vista completa
    fig1, ax1 = plt.subplots(figsize=(10, 4))
    ax1.plot(t_total, resultado, lw=0.5, color="steelblue")
    ax1.set_xlabel("Tiempo (s)")
    ax1.set_ylabel("Amplitud")
    ax1.set_title(f"sweep × filtro_inverso — SNR pico/piso ≈ {snr_db:.1f} dB")
    fig1.tight_layout()
    path1 = OUTPUT_DIR / "convolucion_completa.png"
    fig1.savefig(path1, dpi=150, bbox_inches="tight")
    plt.close(fig1)
    print(f"  Guardado: {path1}")

    # Zoom ±5 ms alrededor del pico
    ventana_ms = 5
    mascara_zoom = np.abs(t_relativo) <= ventana_ms
    fig2, ax2 = plt.subplots(figsize=(10, 4))
    ax2.plot(t_relativo[mascara_zoom], resultado[mascara_zoom],
             lw=1.2, color="steelblue")
    ax2.set_xlabel("Tiempo respecto al pico (ms)")
    ax2.set_ylabel("Amplitud")
    ax2.set_title("Zoom ±5 ms: aproximacion al impulso δ(t)")
    fig2.tight_layout()
    path2 = OUTPUT_DIR / "convolucion_zoom.png"
    fig2.savefig(path2, dpi=150, bbox_inches="tight")
    plt.close(fig2)
    print(f"  Guardado: {path2}")


if __name__ == "__main__":
    grafico_ruido_rosa()
    grafico_sweep()
    grafico_convolucion()
    print("\nListo. Graficos generados en docs/m1/")
    print("  (Los espectrogramas de Audacity ya estan en la carpeta)")
