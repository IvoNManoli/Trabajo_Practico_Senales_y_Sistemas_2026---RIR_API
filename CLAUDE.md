# RIR-API · Señales y Sistemas · UNTREF

Contexto para Claude Code. Leer antes de tocar cualquier archivo.

## El proyecto

API REST en Python (FastAPI) para calcular parámetros acústicos según ISO 3382.
Materia: Señales y Sistemas, carrera Ingeniería de Sonido, UNTREF.

**Integrantes y roles:**
- Ivo Manoli (legajo 64189) — procesamiento de RI → rama `feature/procesamiento-de-RI`
- Agustín Birarelli (legajo 69574) — generación de señales → rama `feature/generacion-de-senales`
- Gaspar Dallinge (legajo 62751) — testing/CI y documentación

## Estado actual

- **M1 (Generación):** completo. Tag `v0.1.0` en main.
- **M2 (Procesamiento):** implementado, con tests y PRs mergeados en main. Pendiente el tag hasta confirmar que no hay correcciones.
- **M3 (Producto final):** pendiente. Vence 7 de julio de 2026.

## Pendiente para cerrar M2

Una vez confirmado que no hay correcciones, crear el tag en main:

```bash
git checkout main && git pull origin main
git tag -a v0.2.0 -m "M2: procesamiento de RI"
git push origin v0.2.0
```

## M2 — ya implementado

Todo en `app/services/`. Funciones completadas:

| Función | Archivo | Estado |
|---|---|---|
| `cargar_audio` | `signal_utils.py` | ✓ |
| `sintetizar_ri` | `signal_utils.py` | ✓ |
| `obtener_ri_desde_sweep` | `signal_utils.py` | ✓ |
| `a_escala_log` | `signal_utils.py` | ✓ |
| `filtro_octava` | `filter.py` | ✓ |

Tests en `tests/test_procesamiento.py`: 13/13 en verde.

**Decisiones de implementación que hay que saber para M3:**
- `filtro_octava` usa `filtfilt` (fase cero). Crítico para que EDT y T60 sean correctos.
- `obtener_ri_desde_sweep` recorta desde `argmax(|ri_full|)` — el pico es el sonido directo, no la muestra 0.
- `a_escala_log` aplica el floor de −120 dB antes del log (valor lineal `1e-6`), no después.
- `sintetizar_ri` importa `filtro_octava` dentro de la función para evitar importación circular.

## Arquitectura — tres capas, nunca mezclar

```
routers/   → reciben HTTP, llaman services, devuelven JSON. No calculan.
services/  → funciones puras DSP. Entran numpy arrays, salen numpy arrays.
             NO saben de HTTP, JSON ni FastAPI.
schemas/   → modelos Pydantic para validación de entrada/salida.
```

## M3 — funciones a implementar

Todo va en `app/services/acoustic_parameters.py`. Rama de trabajo: crear `feature/analisis-acustico`.

### `acoustic_parameters.py`

```python
def suavizar_signal(signal: np.ndarray, ventana: int | str = 'hilbert') -> np.ndarray:
    # Si ventana='hilbert': envolvente instantánea via scipy.signal.hilbert.
    # Si ventana=int: media móvil de la energía (signal**2) con esa ventana.
    # Hilbert es preferible: no requiere elegir tamaño de ventana.

def integral_schroeder(ri: np.ndarray) -> np.ndarray:
    # Integración inversa de la energía: sum de h²[k] desde n hasta N.
    # energia = ri**2
    # integral = np.cumsum(energia[::-1])[::-1]
    # Devolver en dB normalizado a 0 dB: 10*log10(integral / integral[0] + eps)

def regresion_lineal(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    # Mínimos cuadrados. Devolver (pendiente, ordenada, R²).
    # Implementar manualmente (no np.polyfit) para demostrar comprensión.
    # La pendiente en dB/s permite calcular T60 = -60 / pendiente.

def calcular_parametros_acusticos(ri: np.ndarray, fs: int) -> dict[str, dict[float, float]]:
    # Calcula EDT, T10, T20, T30, D50, C80 por banda de octava.
    # Bandas: 125, 250, 500, 1000, 2000, 4000 Hz.
    # Para cada banda: filtro_octava → integral_schroeder → regresion_lineal en rangos ISO 3382.
    # EDT:  regresión entre  0 dB y -10 dB, extrapolar a -60 dB → T = -60/pendiente
    # T10:  regresión entre -5 dB y -15 dB, extrapolar a -60 dB
    # T20:  regresión entre -5 dB y -25 dB, extrapolar a -60 dB
    # T30:  regresión entre -5 dB y -35 dB, extrapolar a -60 dB
    # D50:  sum(h²[:N_50ms]) / sum(h²) * 100  donde N_50ms = int(0.05 * fs)
    # C80:  10*log10(sum(h²[:N_80ms]) / sum(h²[N_80ms:]))  donde N_80ms = int(0.08 * fs)
    # Estructura de retorno: {'EDT': {125: val, 250: val, ...}, 'T30': {...}, ...}
```

### M3 — API REST (FastAPI)

Además de las funciones de análisis, hay que exponer **toda** la funcionalidad (M1 + M2 + M3) como endpoints. Los routers van en `app/routers/`, los schemas en `app/schemas/`.

**Endpoints mínimos:**

| Endpoint | Método | Qué hace |
|---|---|---|
| `/health` | GET | Health check (ya existe) |
| `/api/v1/signals/pink-noise` | POST | Genera ruido rosa → devuelve WAV |
| `/api/v1/signals/sine-sweep` | POST | Genera sine sweep → devuelve WAV |
| `/api/v1/signals/synthetic-ir` | POST | Genera RI sintética con T60 por banda → devuelve WAV |
| `/api/v1/filters/band` | POST | Filtra audio subido por banda de octava → devuelve WAV |
| `/api/v1/filters/frequencies` | GET | Lista frecuencias centrales disponibles |
| `/api/v1/acoustics/parameters` | POST | Recibe WAV, calcula EDT/T10/T20/T30/D50/C80 por banda |
| `/api/v1/utils/schroeder` | POST | Devuelve curva de Schroeder de una RI |
| `/api/v1/utils/log-scale` | POST | Convierte señal a escala dB |

**Reglas de los routers:**
- Aceptar uploads de audio via `multipart/form-data` con `python-multipart`.
- Devolver WAV como `StreamingResponse` con `media_type="audio/wav"`.
- Validar con schemas Pydantic (rangos, tipos).
- HTTP 400 para errores de dominio, 422 para validación, 500 para errores inesperados.

### M3 — Tests requeridos (`tests/test_analisis.py`)

```python
# suavizar_signal
def test_suavizar_hilbert_envolvente()   # salida no negativa y misma longitud
def test_suavizar_media_movil_longitud() # misma longitud que entrada

# integral_schroeder
def test_schroeder_maximo_cero_db()      # primer valor = 0 dB
def test_schroeder_decreciente()         # curva monótonamente decreciente
def test_schroeder_ri_sintetizada()      # pendiente ≈ -60/T60 dB/s

# regresion_lineal
def test_regresion_lineal_exacta()       # datos perfectamente lineales → R²=1
def test_regresion_lineal_pendiente()    # pendiente correcta con datos conocidos

# calcular_parametros_acusticos
def test_parametros_ri_sintetizada()     # T30 dentro de ±10% del T60 conocido
def test_d50_rango()                     # D50 entre 0% y 100%
def test_c80_consistencia()              # C80 > 0 si hay mucha energía temprana

# API (tests/test_api.py, usar fastapi.testclient.TestClient)
def test_health_endpoint()
def test_analysis_endpoint()             # enviar WAV, verificar respuesta JSON con T30, EDT, etc.
def test_invalid_file_returns_422()
```

### M3 — Validación final obligatoria

Comparar resultados de RIR-API con REW (Room EQ Wizard, gratuito) usando RIs reales de OpenAIR:
- Tolerancia: **±0.5 s** para EDT, T20, T30. **±1 dB** para C80.
- Incluir tabla de comparación en el informe (ver `docs/m3/m3_consigna.md`).
- Tag `v1.0.0` en main al entregar. Release en GitHub con changelog.

## Reglas de código

- Docstrings NumPy en toda función pública.
- Type hints en parámetros y retorno.
- Usar `filtfilt` (no `lfilter`) para evitar distorsión de fase.
- Normalizar señales: `signal / np.max(np.abs(signal)) * 0.9`.
- Tests corren con: `uv run pytest -v`
- Linter: `uv run ruff check app/ tests/`

## Cómo correr el proyecto

```bash
uv sync
uv run uvicorn app.main:app --reload   # API en http://localhost:8000
uv run pytest -v                        # tests
uv run python docs/m1/generar_graficos.py  # regenerar gráficos M1
```

## Git

- `main` protegida — solo merge via pull request.
- Ramas: `feature/nombre-descriptivo`.
- Commits: `feat:`, `fix:`, `test:`, `docs:` (Conventional Commits).
- M3 se entrega con tag `v1.0.0` en main.
