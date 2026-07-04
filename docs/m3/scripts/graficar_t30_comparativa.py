"""Graficos de barras T30 (RIR-API vs REW) por banda de octava.

Lee las tablas de validacion ya generadas por comparar_rew_vs_api.py
(docs/m3/tablas_validacion/*_validacion.csv) y compara, para cada RI,
el T30 obtenido con RIR-API contra el reportado por REW.

Uso:
    uv run python docs/m3/scripts/graficar_t30_comparativa.py
"""

import csv
import os

import matplotlib.pyplot as plt
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_DIR = os.path.join(SCRIPT_DIR, "../tablas_validacion")
OUT_DIR = os.path.join(SCRIPT_DIR, "../Imagenes")
os.makedirs(OUT_DIR, exist_ok=True)

BANDAS = [125, 250, 500, 1000, 2000, 4000]

# Paleta categorica fija: RIR-API siempre azul, REW siempre rojo.
COLOR_API = "#2a78d6"
COLOR_REW = "#e34948"
COLOR_GRID = "#e1e0d9"
COLOR_TEXT_SEC = "#52514e"

# (nombre_a_mostrar, archivo_csv)
FUENTES = [
    ("Elveden Hall", "(REW)RT60_elveden_hall_validacion.csv"),
    ("RI sintética (T60=1.5s)", "(REW)RT60_ri_sintetica_t60_1.5s_validacion.csv"),
    ("Maes Howe", "RT60_maes_howe_validacion.csv"),
    ("RI procesada (medida)", "RT60_ri_procesada_20260618_1621_validacion.csv"),
]


def leer_t30(ruta_csv: str) -> dict[int, tuple[float, float]]:
    """Lee un CSV de validacion y devuelve {banda_hz: (rew, rir_api)} para T30."""
    datos = {}
    with open(ruta_csv, newline="", encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            if fila["parametro"] != "T30" or not fila["rew"] or not fila["rir_api"]:
                continue
            datos[int(fila["banda_hz"])] = (float(fila["rew"]), float(fila["rir_api"]))
    return datos


def graficar(nombre: str, datos: dict[int, tuple[float, float]]) -> str:
    """Genera el grafico de barras agrupadas T30 (API vs REW) para una RI."""
    bandas = [fc for fc in BANDAS if fc in datos]
    rew = [datos[fc][0] for fc in bandas]
    api = [datos[fc][1] for fc in bandas]

    x = np.arange(len(bandas))
    ancho = 0.34

    fig, ax = plt.subplots(figsize=(10, 6))

    barras_api = ax.bar(x - ancho / 2 - 0.01, api, ancho, label="RIR-API", color=COLOR_API)
    barras_rew = ax.bar(x + ancho / 2 + 0.01, rew, ancho, label="REW", color=COLOR_REW)

    ax.bar_label(barras_api, fmt="%.2f", padding=3, fontsize=9, color=COLOR_TEXT_SEC)
    ax.bar_label(barras_rew, fmt="%.2f", padding=3, fontsize=9, color=COLOR_TEXT_SEC)

    ax.set_xticks(x)
    ax.set_xticklabels([str(fc) for fc in bandas])
    ax.set_xlabel("Frecuencia central de banda [Hz]")
    ax.set_ylabel("T30 [s]")
    ax.set_title(f"{nombre} — T30: RIR-API vs REW")
    ax.legend(frameon=False)
    ax.grid(axis="y", color=COLOR_GRID, linewidth=1, zorder=0)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    ax.set_ylim(0, max(rew + api) * 1.18)
    plt.tight_layout()

    slug = nombre.lower()
    for viejo, nuevo in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u")):
        slug = slug.replace(viejo, nuevo)
    slug = "".join(c if c.isalnum() else "_" for c in slug).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")

    out = os.path.join(OUT_DIR, f"t30_comparativa_{slug}.png")
    plt.savefig(out, dpi=150)
    plt.close(fig)
    return out


def main() -> None:
    for nombre, archivo in FUENTES:
        ruta_csv = os.path.join(CSV_DIR, archivo)
        if not os.path.exists(ruta_csv):
            print(f"Aviso: no existe {ruta_csv}, se omite {nombre}")
            continue
        datos = leer_t30(ruta_csv)
        out = graficar(nombre, datos)
        print("Guardado:", out)


if __name__ == "__main__":
    main()
