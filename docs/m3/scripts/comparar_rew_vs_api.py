"""Convierte exportacion de REW a DataFrame y compara con RIR-API.

Formato REW (V5.20.13) — columnas por indice al hacer split():
  0: freq     1: BW        2: EDT    3: r
  4: T20      5: r         6: T30    7: r
  8: Topt     9: r        10: ToptStart  11: ToptEnd
  12: T60M   13: "Zero"   14: "Phase"   15: C50
  16: C80    17: D50      18: TS

"Zero Phase" ocupa dos indices, por eso C80 queda en 16 y D50 en 17.

Uso:
    uv run python docs/m3/scripts/comparar_rew_vs_api.py \\
        docs/m3/tablas_validacion/"(REW)RT60_ri_sintetica_t60_1.5s.txt" \\
        docs/m3/ri_sintetica_t60_1.5s.wav
"""

import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from app.services.acoustic_parameters import calcular_parametros_acusticos  # noqa: E402
from app.services.signal_utils import cargar_audio  # noqa: E402

BANDAS = [125, 250, 500, 1000, 2000, 4000]

# Parametros a comparar: (nombre_api, nombre_rew, unidad, tolerancia_consigna)
PARAMS = [
    ("EDT", "EDT", "s",  0.5),
    ("T20", "T20", "s",  0.5),
    ("T30", "T30", "s",  0.5),
    ("C80", "C80", "dB", 1.0),
    ("D50", "D50", "%",  None),
]


# ---------------------------------------------------------------------------
# Parseo del archivo REW
# ---------------------------------------------------------------------------

def parsear_rew_txt(ruta: Path) -> dict[int, dict[str, float]]:
    """Extrae las filas de octava (BW "1/1") del archivo REW.

    No depende de la linea de seccion "Octave filtered data": algunas
    versiones de REW (p. ej. V5.31.3) no la incluyen. Tampoco asume que
    la columna de fase ("Zero Phase", "Forward", "Reverse") ocupe una
    cantidad fija de palabras: C50/C80/D50/TS se leen contando desde el
    final de la linea en lugar de por indice fijo.

    Parameters
    ----------
    ruta : Path
        Ruta al archivo .txt exportado por REW.

    Returns
    -------
    dict[int, dict[str, float]]
        {frecuencia_hz: {"EDT": ..., "T20": ..., "T30": ..., "C80": ..., "D50": ...}}
    """
    resultado: dict[int, dict[str, float]] = {}

    with open(ruta, encoding="utf-8", errors="replace") as f:
        for linea in f:
            partes = linea.split()
            if len(partes) < 17 or partes[1] != "1/1":
                continue

            try:
                freq = int(partes[0])
            except ValueError:
                continue

            if freq not in BANDAS:
                continue

            resultado[freq] = {
                "EDT": float(partes[2]),
                "T20": float(partes[4]),
                "T30": float(partes[6]),
                "C80": float(partes[-3]),
                "D50": float(partes[-2]),
            }

    return resultado


def rew_a_tabla(rew: dict) -> str:
    """Devuelve el contenido REW como tabla de texto."""
    cabecera = f"{'Banda':>6}  {'EDT':>7}  {'T20':>7}  {'T30':>7}  {'C80':>7}  {'D50':>7}"
    separador = "  ".join(["-" * 6] + ["-" * 7] * 5)
    filas = [cabecera, separador]
    for fc in BANDAS:
        d = rew.get(fc, {})
        fila = (
            f"{fc:>6}  "
            f"{d.get('EDT', float('nan')):>7.3f}  "
            f"{d.get('T20', float('nan')):>7.3f}  "
            f"{d.get('T30', float('nan')):>7.3f}  "
            f"{d.get('C80', float('nan')):>7.2f}  "
            f"{d.get('D50', float('nan')):>7.1f}"
        )
        filas.append(fila)
    return "\n".join(filas)


# ---------------------------------------------------------------------------
# Tabla de comparacion
# ---------------------------------------------------------------------------

def _filas_comparacion(rew: dict, api: dict) -> list[dict]:
    """Genera las filas de la tabla de comparacion como lista de dicts."""
    filas = []
    for nombre_api, nombre_rew, unidad, tolerancia in PARAMS:
        for fc in BANDAS:
            val_rew = rew.get(fc, {}).get(nombre_rew)
            val_api = api.get(nombre_api, {}).get(float(fc))

            if val_rew is None or val_api is None:
                filas.append({
                    "parametro": nombre_api,
                    "unidad": unidad,
                    "banda_hz": fc,
                    "rew": None,
                    "rir_api": None,
                    "diferencia": None,
                    "tolerancia": tolerancia,
                    "dentro_tolerancia": None,
                })
                continue

            delta = round(val_api - val_rew, 4)
            dentro = (abs(delta) <= tolerancia) if tolerancia is not None else None

            filas.append({
                "parametro": nombre_api,
                "unidad": unidad,
                "banda_hz": fc,
                "rew": round(val_rew, 4),
                "rir_api": round(val_api, 4),
                "diferencia": delta,
                "tolerancia": tolerancia,
                "dentro_tolerancia": dentro,
            })
    return filas


def guardar_csv(filas: list[dict], ruta: Path) -> None:
    """Guarda la tabla de comparacion como CSV (UTF-8)."""
    campos = ["parametro", "unidad", "banda_hz", "rew", "rir_api",
              "diferencia", "tolerancia", "dentro_tolerancia"]
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        writer.writerows(filas)
    print(f"CSV guardado: {ruta}")


def tabla_comparacion(filas: list[dict]) -> None:
    """Imprime la tabla de validacion requerida por la consigna M3."""
    print()
    ancho = 76
    print("=" * ancho)
    print(f"  {'Parametro':<8}  {'Banda':>6}  {'REW':>8}  {'RIR-API':>8}  {'Dif':>8}  {'Tol':>5}  OK")
    print("-" * ancho)

    parametro_actual = None
    for f in filas:
        if f["parametro"] != parametro_actual:
            if parametro_actual is not None:
                print("-" * ancho)
            parametro_actual = f["parametro"]

        if f["rew"] is None:
            print(f"  {f['parametro']:<8}  {f['banda_hz']:>6}  {'N/A':>8}  {'N/A':>8}  {'-':>8}  {'-':>5}  -")
            continue

        tol_str = f"+/-{f['tolerancia']}" if f["tolerancia"] else "-"
        ok = ("OK" if f["dentro_tolerancia"] else "FAIL") if f["dentro_tolerancia"] is not None else "-"

        print(
            f"  {f['parametro']:<8}  {f['banda_hz']:>6}  {f['rew']:>8.3f}  {f['rir_api']:>8.3f}"
            f"  {f['diferencia']:>+8.3f}  {tol_str:>5}  {ok}"
        )

    print("-" * ancho)
    print("=" * ancho)
    print("  Tolerancias (consigna M3): +/-0.5 s para EDT/T20/T30  |  +/-1 dB para C80")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    ruta_rew = Path(sys.argv[1])
    ruta_wav = Path(sys.argv[2])

    print(f"\nREW:     {ruta_rew.name}")
    print(f"WAV:     {ruta_wav.name}")

    # --- REW ---
    rew = parsear_rew_txt(ruta_rew)
    print(f"\n{'-'*50}")
    print("  Resultados REW (octava filtrada)")
    print(f"{'-'*50}")
    print(rew_a_tabla(rew))

    # --- RIR-API ---
    ri, fs = cargar_audio(ruta_wav)
    api = calcular_parametros_acusticos(ri, fs)

    print(f"\n{'-'*50}")
    print("  Resultados RIR-API")
    print(f"{'-'*50}")
    cabecera = f"{'Banda':>6}  {'EDT':>7}  {'T20':>7}  {'T30':>7}  {'C80':>7}  {'D50':>7}"
    print(cabecera)
    print("  ".join(["-" * 6] + ["-" * 7] * 5))
    for fc in BANDAS:
        edt = api["EDT"].get(float(fc))
        t20 = api["T20"].get(float(fc))
        t30 = api["T30"].get(float(fc))
        c80 = api["C80"].get(float(fc))
        d50 = api["D50"].get(float(fc))
        fmt = lambda v, d: f"{v:>7.{d}f}" if v is not None else f"{'N/A':>7}"  # noqa: E731
        print(f"{fc:>6}  {fmt(edt,3)}  {fmt(t20,3)}  {fmt(t30,3)}  {fmt(c80,2)}  {fmt(d50,1)}")

    # --- Comparacion y CSV ---
    filas = _filas_comparacion(rew, api)

    ruta_csv = ruta_rew.with_name(ruta_rew.stem + "_validacion.csv")
    guardar_csv(filas, ruta_csv)

    print(f"\n{'-'*76}")
    print("  TABLA DE VALIDACION  (RIR-API vs REW)")
    tabla_comparacion(filas)


if __name__ == "__main__":
    main()
