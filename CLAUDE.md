# RIR-API · Señales y Sistemas · UNTREF

Contexto para Claude Code. Leer antes de tocar cualquier archivo.

## El proyecto

API REST en Python (FastAPI) para calcular parámetros acústicos según ISO 3382.
Materia: Señales y Sistemas, carrera Ingeniería de Sonido, UNTREF.

**Integrantes y roles:**
- Ivo Manoli (legajo 64189) — procesamiento de RI → rama `feature/procesamiento-de-RI`
- Ivo Manoli (legajo 64189) — generación de señales → rama `feature/generacion-de-senales`
- Gaspar Dallinge (legajo 62751) — testing/CI y documentación

## Estado actual

- **M1 (Generación):** completo. Tag `v0.1.0` en main.
- **M2 (Procesamiento):** completo. Tag `v0.2.0` en main.
- **M3 (Producto final):** desarrollo completo (funciones, API REST, tests, informe y validación contra REW). **Solo falta el tag `v1.0.0` en main y el release en GitHub con changelog.**

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

## M3 — ya implementado

Todo en `app/services/acoustic_parameters.py` (más `convolution.py` para la convolución de validación). Funciones completadas:

| Función | Archivo | Estado |
|---|---|---|
| `suavizar_signal` | `acoustic_parameters.py` | ✓ |
| `integral_schroeder` | `acoustic_parameters.py` | ✓ |
| `regresion_lineal` | `acoustic_parameters.py` | ✓ |
| `metodo_lundeby` | `acoustic_parameters.py` | ✓ |
| `calcular_parametros_acusticos` | `acoustic_parameters.py` | ✓ |
| `convolucionar` | `convolution.py` | ✓ |

Tests en `tests/test_analisis.py` (19) y `tests/test_convolucion.py` (6): todos en verde.

**Decisiones de implementación que hay que saber:**
- `calcular_parametros_acusticos` devuelve EDT, T10, T20, T30, D50, C80 y SNR, para las 8 bandas de octava (125 Hz a 16 kHz).
- `metodo_lundeby`: se probaron dos correcciones propias (acotar la regresión preliminar a 4x el tiempo de caída de 20 dB, y exigir cruces sostenidos vía `_primer_cruce_sostenido` para no confundir nulos modales con el piso de ruido) y se revirtieron ambas. Se optó por ceñirse al algoritmo literal de 6 pasos que pide la consigna de M3 (cruce preliminar = primer intervalo bajo "ruido + 10 dB", sin mínimos ni sostenimiento), ya que `metodo_lundeby` es función extra opcional y no vale la pena cargarla con heurísticas propias no pedidas.
- `filtro_octava` usa `sosfiltfilt`, no `filtfilt` con coeficientes `b, a` directos. En bandas bajas (125 Hz) con orden 4 (8 polos reales por la transformación pasabajos→pasabanda), la forma directa da `NaN` por mal condicionamiento numérico — verificado empíricamente, no es una preferencia estética.
- `cargar_audio` (M2) no promedia canales de una señal estéreo (downmix) — selecciona un solo canal (parámetro `canal`, por defecto `"L"`). Promediar introduce cancelaciones tipo filtro peine entre canales desfasados.
- `_calcular_tiempo()` (interna) centraliza el criterio de validez de un ajuste (R² < 0.8 o pendiente positiva → `None`), usado por EDT/T10/T20/T30 para no duplicar esa lógica cuatro veces.
- `/api/v1/acoustics/parameters` devuelve un valor **global** por parámetro (promedio de las bandas de 500 y 1000 Hz, o la que esté disponible si falta una), no un desglose por banda — ese desglose es responsabilidad exclusiva de `/parameters/by-bands`. Antes ambos endpoints devolvían lo mismo por banda; se corrigió en `app/routers/acoustics.py`.

### API REST (FastAPI) — implementada

Routers en `app/routers/` (uno por dominio: `health.py`, `signals.py`, `filters.py`, `acoustics.py`, `analysis.py`, `utils.py`, `convolution.py`), registrados en `app/main.py`. Schemas Pydantic en `app/schemas/`.

**Endpoints:**

| Endpoint | Método | Qué hace |
|---|---|---|
| `/health` | GET | Health check |
| `/api/v1/signals/pink-noise` | POST | Genera ruido rosa → WAV |
| `/api/v1/signals/sine-sweep` | POST | Genera sine sweep → WAV |
| `/api/v1/signals/sine-sweep-pair` | POST | Sweep + filtro inverso → ZIP |
| `/api/v1/signals/synthetic-ir` | POST | Genera RI sintética con T60 por banda → WAV |
| `/api/v1/filters/frequencies` | GET | Lista frecuencias centrales disponibles |
| `/api/v1/filters/band` | POST | Filtra audio subido por banda de octava → WAV |
| `/api/v1/acoustics/parameters` | POST | EDT/T10/T20/T30/D50/C80, valor global (promedio 500+1000 Hz) → JSON |
| `/api/v1/acoustics/parameters/by-bands` | POST | Mismo cálculo, detallado por banda de octava |
| `/api/v1/analysis/impulse-response` | POST | Análisis completo de una RI → JSON |
| `/api/v1/utils/schroeder` | POST | Curva de Schroeder de una RI → JSON |
| `/api/v1/utils/smoothing` | POST | Envolvente suavizada → JSON |
| `/api/v1/utils/log-scale` | POST | Señal en escala dB → JSON |
| `/api/v1/convolution/with-ir` | POST | Convoluciona audio con una RI subida → WAV |
| `/api/v1/convolution/with-synthetic-ir` | POST | Convoluciona audio con una RI sintética → WAV |

**Reglas de los routers (ya aplicadas):**
- Uploads de audio via `multipart/form-data`.
- WAV devuelto como `StreamingResponse` con `media_type="audio/wav"`.
- Validación con schemas Pydantic (rangos, tipos) para los endpoints de entrada JSON.
- HTTP 400 para errores de dominio, 422 para validación/lectura, 500 para errores inesperados.

Tests en `tests/test_api.py`: 24/24 en verde.

### Validación final — hecha

Comparación contra REW (Room EQ Wizard) con 3 RIs: Elveden Hall y Maes Howe (OpenAIR) más una RI propia medida con `medir_ri.py`. T20 y T30 quedan dentro de ±0.5 s en las 3 RIs y en las 6 bandas exigidas (125–4000 Hz); peor caso: T30 a 125 Hz en Elveden Hall, 0.48 s de diferencia. Tablas y gráficos completos en `docs/informe.md` (sección 4.3) y `docs/m3/validacion_m3.md`.

**Único pendiente de M3: tag `v1.0.0` en main + release en GitHub con changelog.**

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
- **Pendiente:** tag `v1.0.0` en main + release en GitHub con changelog, para cerrar la entrega de M3.
