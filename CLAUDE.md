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
- **M2 (Procesamiento):** pendiente. Vence **16 de junio de 2026**. Es la próxima sesión.
- **M3 (Producto final):** pendiente. Vence 7 de julio de 2026.

## Arquitectura — tres capas, nunca mezclar

```
routers/   → reciben HTTP, llaman services, devuelven JSON. No calculan.
services/  → funciones puras DSP. Entran numpy arrays, salen numpy arrays.
             NO saben de HTTP, JSON ni FastAPI.
schemas/   → modelos Pydantic para validación de entrada/salida.
```

## M2 — funciones a implementar

Todo va en `app/services/`. Rama de trabajo: `feature/procesamiento-de-RI`.

### `signal_utils.py`

```python
def cargar_audio(ruta: str | Path) -> tuple[np.ndarray, int]:
    # soundfile. Normalizar a float64. Manejar estéreo.
    # Raises FileNotFoundError, ValueError.

def sintetizar_ri(t60_por_banda: dict[float, float], fs: int, duracion: float) -> np.ndarray:
    # h(t) = ruido_blanco * exp(-alpha * t), alpha = 6.908 / T60
    # Por cada banda: filtrar con filtro_octava, aplicar envolvente, sumar.

def obtener_ri_desde_sweep(grabacion: np.ndarray, filtro_inverso: np.ndarray) -> np.ndarray:
    # Deconvolución: fftconvolve(grabacion, filtro_inverso, mode='full')
    # Recortar al pico, normalizar.

def a_escala_log(signal: np.ndarray) -> np.ndarray:
    # 20 * log10(|h| / max|h|). Floor en -120 dB. Evitar log(0).
```

### `filter.py`

```python
def filtro_octava(signal: np.ndarray, fc: float, fs: int, orden: int = 4) -> np.ndarray:
    # IEC 61260: f_inf = fc / sqrt(2), f_sup = fc * sqrt(2)
    # scipy.signal.butter + filtfilt (fase cero, crítico para EDT y T60).
```

### Tests requeridos (`tests/test_procesamiento.py`)

- `cargar_audio`: carga WAV, error si no existe, normalización entre -1 y 1.
- `sintetizar_ri`: duración correcta, decaimiento ≈ T60 especificado (±10%).
- `obtener_ri_desde_sweep`: RI recuperada correlaciona > 0.9 con la original.
- `filtro_octava`: ganancia 0 dB en fc, −3 dB en frecuencias de corte, >20 dB de atenuación a una octava.
- `a_escala_log`: máximo = 0 dB, mitad de amplitud = −6 dB.

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
- M2 se entrega con tag `v0.2.0` en main.
