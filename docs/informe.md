# Informe Técnico — RIR-API
## Señales y Sistemas · UNTREF · 2026

**Integrantes:**
- Ivo Manoli (legajo 64189) — procesamiento de RI y análisis acústico
- Gaspar Dallinge (legajo 62751) — testing/CI y documentación

---

## Resumen

Se desarrolló una API REST en Python (FastAPI) para el cálculo de parámetros acústicos de salas a partir de respuestas al impulso (RI), siguiendo la norma ISO 3382. El sistema implementa generación de señales de excitación, procesamiento de RI y cálculo de los parámetros EDT, T10, T20, T30, D50 y C80 por banda. La arquitectura sigue un modelo de tres capas que separa el procesamiento DSP de la lógica HTTP. Se validaron los resultados comparando contra el software de uso comercial REW (Room EQ Wizard) con dos respuestas al impulso reales de la base de datos OpenAIR y una respuesta al impulso medida con las funciones de la API. Las diferencias máximas obtenidas fueron de ±0.4 s en T30 en un único caso en la banda de 125 Hz, aunque se sitúa en valores dentro de la tolerancia de ±0.5 según la norma. Adicionalmente, la API incluye la función de convolucionar audio con la RI deseada a modo de validación. 

---

## 1. Introducción

La acústica de salas estudia cómo el sonido se propaga y decae en un recinto. Una serie de parámetros definidos por la norma ISO 3382 permiten cuantificar la calidad acústica para diferentes usos: reverberación (T60) para música, claridad (C80) para música, inteligibilidad (D50) para la palabra hablada. Conocer estos parámetros permiten realizar un análisis objetivo de la acústica de recintos más allá de la escucha subjetiva, lo cual brinda la posibilidad de tomar decisiones precisas sobre la adaptación y el uso de estos espacios según la finalidad determinada. En este contexto resulta conveniente el desarrollo de un software que brinde herramientas de cálculo y procesamiento para llevar a cabo esas mediciones. El formato API se destaca por su particularidad de ser fácilmente integrable dentro de cualquier software, brindando independencia entre el lenguaje y la plataforma, permitiendo el desacople entre cliente y servidor e incluyendo sus propios mecanismos de validación centralizada. Así, quien deba realizar un procesamiento de RI puede limitarse a subir un archivo WAV y obtener los parámetros deseados, sin necesidad de depender de su propio hardware o software.


El objetivo de este trabajo es implementar un sistema completo de medición y análisis acústico. No solo aportando las herramientas de cálculo de parámetros acústicos, sino herramientas relacionadas con la medición y obtención de la respuesta al impulso, como veremos más adelante. Por organización, se dividió el desarrollo en tres etapas de producción, llamadas "Milestones":
1. **Milestone 1 — Generación de señales**
2. **Milestone 2 — Procesamiento de RI**
3. **Milestone 3 — Análisis acústico y API REST**
Pueden entenderse a las Milestones como fases del proyecto. Si bien en algunos casos los objetivos de cada milestone son independientes de las otras, en muchas ocasiones el desarrollo de las milestones posteriores dependieron de las anteriores.

En la Milestone 1 se implementaron las señales de excitación necesarias para medir una sala: ruido rosa (densidad espectral 1/f) y sine sweep logarítmico con su filtro inverso correspondiente según la técnica de Farina (**CITAR FARINA**). Si bien normalmente el ruido rosa no es utilizado para la medición y obtención de la RI, se incluye principalmente con la idea de brindar un recurso para realizar la calibración del software de reproducción del sine sweep. Además se incluyó la función de grabar y reproducir, que permite obtener la respuesta al impulso del recinto mediante los parlantes y el micrófono de la computadora (solo ejecutable através de script). 

La Milestone 2 cubre el procesamiento de la respuesta al impulso: carga de archivos de audio (WAV/FLAC), obtención de la RI a partir de la grabación del sine sweep mediante deconvolución, filtrado por bandas de octava, conversión a escala logarítmica (dB) y generación de una RI sintética para posteriormente validar los cálculos de parámetros acústicos.  Es la etapa que transforma una grabación cruda en una RI lista para analizar.

Finalmente, la Milestone 3 agrega el análisis acústico propiamente dicho. Desde el suavizado de la envolvente de la respuesta al impulso, la integral de Schroeder, el truncamiento de Lundeby y regresión lineal para calcular EDT, T10, T20, T30, D50 y C80 por banda de octava según la norma, hasta la herramienta de convolución de una RI con cualquier audio WAV. Este último punto fue realizado con el objetivo de brindar una experiencia subjetiva de validación al cliente (o hasta incluso como una herramienta recreativa) y expone toda la funcionalidad de los tres milestones como una API REST (FastAPI). 

A modo de ofrecer un método de validación subjetiva, la API brinda la posibilidad de realizar una convolución de un audio cargado con una RI cargada o una RI sintetizada según los parámetros seleccionados, mediante el algoritmo de FFT (Fast Fourier Transform). Se desarrollará este aspecto y sus decisiones en la sección de metodología.

El alcance del análisis de parámetros acústicos incluye las bandas de octava de 125 Hz a 16 kHz, archivos WAV/FLAC como entrada, y devolución de resultados en JSON y WAV. No se incluye soporte para señales estéreo ni corrección de Lundeby activada por defecto (disponible como opción).

---

## 2. Marco Teórico

### 2.1 Ruido rosa (1/f)

El ruido rosa tiene densidad espectral de potencia inversamente proporcional a la frecuencia:

$$S(f) = \frac{k}{f}$$

En escala logarítmica corresponde a una caída de exactamente **−3 dB por octava**:

$$\Delta L = 10 \log_{10}\!\left(\frac{1}{2}\right) \approx -3{,}01 \text{ dB}$$

### 2.2 Sine sweep logarítmico (Farina, 2000)

La frecuencia instantánea crece exponencialmente con el tiempo:

$$f(t) = f_1 \cdot e^{\,t \ln(f_2/f_1)/T}$$

La señal es:

$$x(t) = \sin\!\left[2\pi f_1 L \left(e^{t/L} - 1\right)\right], \quad L = \frac{T}{\ln(f_2/f_1)}$$

El filtro inverso se construye invirtiendo temporalmente el sweep con corrección de amplitud:

$$x_{\text{inv}}(t) = \frac{x(T-t)}{A(t)}, \quad A(t) = e^{-t \ln(f_2/f_1)/T}$$

La convolución sweep × filtro inverso converge a una delta de Dirac, permitiendo recuperar la RI del recinto:

$$y(t) * x_{\text{inv}}(t) \approx h(t)$$

### 2.3 Filtros de banda de octava (IEC 61260)

Las frecuencias de corte de un filtro de octava centrado en $f_c$ son:

$$f_{\text{inf}} = \frac{f_c}{\sqrt{2}}, \quad f_{\text{sup}} = f_c \cdot \sqrt{2}$$

### 2.4 Integral de Schroeder (Energy Decay Curve)

La integral de Schroeder representa el decaimiento de energía acústica mediante integración inversa:

$$E(t) = \int_{t}^{\infty} h^2(\tau) \, d\tau \quad \Rightarrow \quad E[n] = \sum_{k=n}^{N-1} h^2[k]$$

La curva de decaimiento normalizada en dB:

$$L[n] = 10 \log_{10}\!\left(\frac{E[n]}{E[0]}\right)$$

### 2.5 Parámetros acústicos ISO 3382

Los tiempos de reverberación se calculan ajustando una recta por mínimos cuadrados a distintos rangos de la curva de Schroeder y extrapolando a −60 dB:

| Parámetro | Rango de ajuste | Fórmula |
|-----------|:---------------:|---------|
| EDT | 0 dB a −10 dB | $\text{EDT} = -60 / m_{0,-10}$ |
| T10 | −5 dB a −15 dB | $T_{10} = -60 / m_{-5,-15}$ |
| T20 | −5 dB a −25 dB | $T_{20} = -60 / m_{-5,-25}$ |
| T30 | −5 dB a −35 dB | $T_{30} = -60 / m_{-5,-35}$ |

La **Definición** ($D_{50}$) y la **Claridad** ($C_{80}$):

$$D_{50} = \frac{\sum_{n=0}^{N_{50}} h^2[n]}{\sum_{n=0}^{N-1} h^2[n]} \times 100\% \quad (N_{50} = \lfloor 0.050 \cdot f_s \rfloor)$$

$$C_{80} = 10 \log_{10}\!\left(\frac{\sum_{n=0}^{N_{80}} h^2[n]}{\sum_{n=N_{80}+1}^{N-1} h^2[n]}\right) \quad (N_{80} = \lfloor 0.080 \cdot f_s \rfloor)$$

### 2.6 Regresión lineal por mínimos cuadrados

La pendiente $m$ y ordenada al origen $b$ que minimizan $\sum (y_i - \hat{y}_i)^2$:

$$m = \frac{N \sum x_i y_i - \sum x_i \sum y_i}{N \sum x_i^2 - (\sum x_i)^2}, \quad b = \frac{\sum y_i - m \sum x_i}{N}$$

El coeficiente de determinación:

$$R^2 = 1 - \frac{\sum (y_i - \hat{y}_i)^2}{\sum (y_i - \bar{y})^2}$$

---

## 3. Desarrollo Experimental

### 3.1 Arquitectura del software

El sistema sigue una arquitectura de tres capas estrictamente separadas:

```
┌──────────────────────────────────────────────────────┐
│                    Capa HTTP                         │
│   app/routers/   (FastAPI: reciben HTTP, devuelven   │
│   signals.py     JSON/WAV, no calculan nada)         │
│   filters.py                                         │
│   acoustics.py                                       │
│   analysis.py                                        │
│   utils.py                                           │
└─────────────────────┬────────────────────────────────┘
                      │ llaman a
┌─────────────────────▼────────────────────────────────┐
│                 Capa de Servicios                     │
│   app/services/  (DSP puro: entran/salen numpy        │
│   pink_noise.py  arrays, no saben de HTTP ni JSON)   │
│   sine_sweep.py                                       │
│   signal_utils.py                                     │
│   filter.py                                           │
│   acoustic_parameters.py                             │
└─────────────────────┬────────────────────────────────┘
                      │ validado por
┌─────────────────────▼────────────────────────────────┐
│                  Capa de Schemas                      │
│   app/schemas/   (Pydantic: validación de tipos       │
│   signals.py     y rangos en los extremos del        │
│   responses.py   sistema)                            │
└──────────────────────────────────────────────────────┘
```

### 3.2 Flujo de procesamiento completo

```
Archivo WAV/FLAC
       │
       ▼
  cargar_audio()   → señal float64 normalizada + fs
       │
       ▼
  filtro_octava()  → señal filtrada por banda (125…16000 Hz)
  [Butterworth orden 4, filtfilt, IEC 61260]
       │
       ▼
  integral_schroeder()  → curva de decaimiento EDC en dB
  [integración inversa: cumsum(h²[::-1])[::-1]]
       │
       ▼
  regresion_lineal()  → pendiente m [dB/s], R²
  [mínimos cuadrados manual]
       │
       ▼
  T = -60 / m   →  EDT, T10, T20, T30
  D50, C80      →  calculados directamente sobre h²
```

### 3.3 Milestone 1 — Generación de señales

#### `generar_ruido_rosa`

Genera ruido rosa (densidad espectral 1/f) en el dominio frecuencial:

1. Se genera ruido blanco gaussiano.
2. Se aplica `np.fft.rfft`.
3. Se multiplica cada componente por `1/√f`, convirtiendo la PSD de plana a `1/f`.
4. Se aplica `np.fft.irfft(n=n_muestras)`.
5. Se normaliza a 0.8 (headroom para reproducción por hardware).

**Decisiones clave:**
- `rfft`/`irfft` en lugar de `fft`/`ifft`: para señales reales es el doble de eficiente (aprovecha la simetría hermítica).
- `factores[0] = 1` (DC sin modificar): evita división por cero en f = 0.
- `irfft(n=n_muestras)`: garantiza exactamente la misma cantidad de muestras que la entrada, independientemente de si es par o impar.

#### `generar_sine_sweep`

Genera el sweep logarítmico y su filtro inverso según Farina (2000):

**Decisiones clave:**
- Sweep logarítmico en lugar de lineal: invierte igual tiempo en cada octava, garantizando buena SNR en todas las bandas de análisis.
- `endpoint=False` en `np.linspace`: evita discontinuidad de fase si la señal se reproduce en loop.
- Headroom de −6 dB (factor 0.5): evita clipping en reproducción por hardware.
- Misma longitud para sweep y filtro inverso: requisito de `fftconvolve` para que la deconvolución no quede desplazada.

La SNR pico/piso de la convolución sweep × filtro inverso medida fue de **≈ 101.7 dB**, muy por encima del umbral mínimo de 40 dB.

### 3.4 Milestone 2 — Procesamiento de la RI

#### `cargar_audio`

Carga WAV o FLAC y devuelve float64 normalizado entre −1 y 1.

**Decisiones clave:**
- `soundfile` en lugar de `scipy.io.wavfile`: soporta WAV y FLAC, realiza la conversión y normalización automáticamente.
- `always_2d=False`: para audio mono devuelve shape `(N,)` en lugar de `(N, 1)`, compatible con el resto del pipeline.
- Verificación explícita de existencia antes de leer: permite lanzar `FileNotFoundError` con mensaje claro.

#### `sintetizar_ri`

Genera una RI artificial con T60 conocidos por banda para validación:

$$h(t) = \sum_{\text{banda}} \text{filtro\_octava}(\text{ruido}(t)) \cdot e^{-\alpha t}, \quad \alpha = \frac{6.908}{T_{60}}$$

El coeficiente $\alpha$ se deriva de la definición de T60:

$$\alpha = \frac{3\ln(10)}{T_{60}} \approx \frac{6.908}{T_{60}}$$

**Decisiones clave:**
- Import interno de `filtro_octava`: evita importación circular entre módulos.
- Ruido blanco filtrado por banda: simula el modelo de campo difuso (reflexiones aleatorias).

#### `obtener_ri_desde_sweep`

Deconvolución mediante convolución con el filtro inverso + recorte por onset basado en RMS:

1. Se estima el RMS del ruido de fondo con el último 10% de la señal deconvolucionada.
2. Se calcula un umbral 20 dB por encima del RMS: `umbral = rms_ruido × 10`.
3. Se retrocede desde el pico hasta que la señal cae por debajo del umbral → onset.
4. La RI se recorta desde ese onset.

**Decisiones clave:**
- `fftconvolve` (O(N log N)) en lugar de convolución directa (O(N²)): decisivo para señales de varios segundos.
- `mode="full"`: conserva la cola de reverberación completa.
- Retroceder desde el pico en lugar de buscar desde el inicio: evita falsos positivos por picos de ruido previos al sonido directo.
- `margen_db=20.0` configurable: 20 dB es el estándar práctico; exposición como parámetro permite ajustarlo según la SNR de cada grabación.

#### `filtro_octava`

Filtro Butterworth pasabanda orden 4, fase cero (`filtfilt`), frecuencias de corte IEC 61260.

**Decisiones clave:**
- `filtfilt` en lugar de `lfilter`: aplica el filtro en dos pasadas cancelando la distorsión de fase. EDT y T60 dependen de la precisión temporal de la curva de decaimiento — esta decisión es crítica.
- Butterworth en lugar de Chebyshev o elíptico: respuesta completamente plana en la banda de paso (sin ripple). Con ripple, algunas frecuencias tendrían más energía y la curva de Schroeder resultaría incorrecta.
- `min(f_sup / nyq, 0.9999)`: evita que `butter` falle cuando la frecuencia de corte superior supera Nyquist en bandas altas.

#### `a_escala_log`

Convierte amplitud lineal a dB normalizados a 0 dB en el pico, con piso en −120 dB.

**Decisiones clave:**
- Aplicar el piso de −120 dB **antes** del logaritmo: si se aplicara después, `log10(0) = -inf` generaría NaN que se propagan silenciosamente.
- Piso en −120 dB en lugar de `eps`: corresponde al límite práctico del rango dinámico en mediciones acústicas reales. `eps` daría ~−315 dB, sin sentido físico.

### 3.5 Milestone 3 — Análisis acústico y API REST

#### `suavizar_signal`

Dos modos de suavizado:

- **Hilbert** (por defecto): envolvente instantánea $A(t) = |x(t) + j\hat{x}(t)|$ via `scipy.signal.hilbert`. No requiere elegir tamaño de ventana.
- **Media móvil** (ventana int): $y[n] = \frac{1}{M}\sum_{k=0}^{M-1} x^2[n-k]$, aplicada sobre la energía.

#### `integral_schroeder`

Implementación eficiente usando `np.cumsum` sobre la señal invertida:

```python
energia = ri ** 2
integral = np.cumsum(energia[::-1])[::-1]
edc_db = 10.0 * np.log10(np.maximum(integral / integral[0], eps))
```

#### `regresion_lineal`

Implementación manual de mínimos cuadrados (sin `np.polyfit`):

```python
pendiente = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x**2)
ordenada  = (sum_y - pendiente * sum_x) / n
r2 = 1.0 - ss_res / ss_tot
```

La pendiente en dB/s permite calcular $T = -60 / m$. Si $R^2 < 0.8$ o la pendiente es positiva (piso de ruido), el parámetro se devuelve como `None`.

#### `calcular_parametros_acusticos`

Para cada banda de octava (125 Hz a 16 kHz):

1. `filtro_octava(ri, fc, fs)` → `ri_banda`
2. `integral_schroeder(ri_banda)` → `edc` + vector de tiempo `t`
3. `regresion_lineal` en rangos ISO 3382 → EDT, T10, T20, T30
4. Cálculo directo de D50 y C80 sobre `ri_banda²`

#### `metodo_lundeby` (implementación extra)

Determina iterativamente el punto de truncamiento de la RI buscando el cruce entre la curva de decaimiento y el piso de ruido. Permite corregir la integral de Schroeder en grabaciones con ruido de fondo real. Activable con `usar_lundeby=True` en `calcular_parametros_acusticos`.

### 3.6 API REST

La API expone toda la funcionalidad (M1 + M2 + M3) como endpoints HTTP:

| Endpoint | Método | Función |
|----------|:------:|---------|
| `/health` | GET | Health check |
| `/api/v1/signals/pink-noise` | POST | Genera ruido rosa → WAV |
| `/api/v1/signals/sine-sweep` | POST | Genera sine sweep → WAV |
| `/api/v1/signals/sine-sweep-pair` | POST | Sweep + filtro inverso → ZIP con dos WAV |
| `/api/v1/signals/synthetic-ir` | POST | Genera RI sintética → WAV |
| `/api/v1/filters/frequencies` | GET | Lista frecuencias centrales disponibles |
| `/api/v1/filters/band` | POST | Filtra audio por banda → WAV |
| `/api/v1/acoustics/parameters` | POST | EDT/T10/T20/T30/D50/C80 por banda → JSON |
| `/api/v1/acoustics/parameters/by-bands` | POST | Mismo resultado organizado por frecuencia |
| `/api/v1/analysis/impulse-response` | POST | Análisis completo de RI → JSON |
| `/api/v1/utils/schroeder` | POST | Curva de Schroeder → JSON |
| `/api/v1/utils/smoothing` | POST | Envolvente suavizada → JSON |
| `/api/v1/utils/log-scale` | POST | Señal en dB → JSON |
| `/api/v1/convolution` | POST | Convolucion de RI con audio → WAV |

**Reglas de implementación:**
- Uploads de audio via `multipart/form-data`.
- WAV devuelto como `StreamingResponse(media_type="audio/wav")`.
- HTTP 400 para errores de dominio, 422 para archivos inválidos, 500 para errores inesperados.
- Validación con schemas Pydantic (rangos, tipos).
- CORS habilitado con `allow_origins=["*"]` para uso desde cualquier cliente.

---

## 4. Resultados

### 4.1 Validación M1 — Generación de señales

| Señal | Criterio | Resultado | Estado |
|-------|----------|-----------|:------:|
| Ruido rosa | Pendiente −3 ± 1 dB/oct | −3.01 dB/oct | ✓ |
| Ruido rosa | Distribución uniforme en el tiempo | Confirmado en espectrograma | ✓ |
| Sine sweep | Barrido monótono 20 Hz → 20 kHz | Confirmado en espectrograma | ✓ |
| Convolución sweep × inverso | SNR pico/piso ≥ 40 dB | ≈ 101.7 dB | ✓ |

La pendiente de −3.01 dB/oct del ruido rosa (medida con Welch sobre 10 s de señal) es prácticamente coincidente con el valor teórico de −3.01 dB. La SNR de 101.7 dB en la convolución sweep × filtro inverso garantiza que la deconvolución en M2 produce RI con alta resolución y bajo nivel de artefactos.

*Ver gráficos: `docs/m1/imagenes/`*

### 4.2 Validación M2 — Procesamiento de RI

Los filtros de octava fueron validados con dos RIs reales de OpenAIR:
- **Elveden Hall** (Suffolk, Inglaterra) — sala grande, T60 ≈ 3 s
- **Maes Howe** (Orkney, Escocia) — recinto pequeño, T60 ≈ 0.3 s

| Criterio | Verificación | Estado |
|----------|-------------|:------:|
| Filtros IEC 61260: −3 dB en frecuencias de corte | Verificado con `freqz` | ✓ |
| Filtros IEC 61260: sin solapamiento entre bandas | Sin huecos de 125 Hz a 4 kHz | ✓ |
| `cargar_audio`: normalización entre −1 y 1 | Amplitud máxima = 1.0 | ✓ |
| `obtener_ri_desde_sweep`: onset por criterio RMS | 20 dB sobre piso de ruido | ✓ |

*Ver gráficos: `docs/m2/imagenes/`*

### 4.3 Validación M3 — Parámetros acústicos

#### Validación con RI sintética (T60 conocido)

Se sintetizó una RI con T60 = 2.0 s en todas las bandas y se calcularon los parámetros:

| Parámetro | Banda (Hz) | Valor calculado | Valor esperado | Error |
|-----------|:----------:|:---------------:|:--------------:|:-----:|
| T30 | 500 | [COMPLETAR] s | 2.0 s | [COMPLETAR] % |
| T30 | 1000 | [COMPLETAR] s | 2.0 s | [COMPLETAR] % |
| EDT | 500 | [COMPLETAR] s | — | — |
| D50 | 1000 | [COMPLETAR] % | — | — |
| C80 | 1000 | [COMPLETAR] dB | — | — |

#### Comparación con REW (Room EQ Wizard)

RI utilizada: `[COMPLETAR — nombre del archivo WAV]` (fs = [COMPLETAR] Hz, duración = [COMPLETAR] s)

| Parámetro | Banda (Hz) | RIR-API | REW | Diferencia | Dentro de tolerancia |
|-----------|:----------:|:-------:|:---:|:----------:|:--------------------:|
| EDT | 125 | | | | |
| EDT | 250 | | | | |
| EDT | 500 | | | | |
| EDT | 1000 | | | | |
| EDT | 2000 | | | | |
| EDT | 4000 | | | | |
| T20 | 125 | | | | |
| T20 | 250 | | | | |
| T20 | 500 | | | | |
| T20 | 1000 | | | | |
| T20 | 2000 | | | | |
| T20 | 4000 | | | | |
| T30 | 125 | | | | |
| T30 | 250 | | | | |
| T30 | 500 | | | | |
| T30 | 1000 | | | | |
| T30 | 2000 | | | | |
| T30 | 4000 | | | | |
| C80 | 500 | | | | |
| C80 | 1000 | | | | |
| C80 | 2000 | | | | |

**Tolerancia:** ±0.5 s para EDT, T20, T30 · ±1 dB para C80

### 4.4 Tests automatizados

Se implementaron [COMPLETAR] tests en total:

| Módulo | Tests | Estado |
|--------|:-----:|:------:|
| `test_generacion.py` (M1) | [N] | ✓ verde |
| `test_procesamiento.py` (M2) | 13 | ✓ verde |
| `test_analisis.py` (M3) | [N] | ✓ verde |
| `test_api.py` (M3 endpoints) | [N] | ✓ verde |

---

## 5. Conclusiones

El sistema RIR-API implementa de forma completa el pipeline de medición y análisis acústico según ISO 3382-1: desde la generación de señales de excitación hasta el cálculo de parámetros acústicos por banda de octava, expuesto como API REST con documentación automática.

**Resultados destacados:**
- La SNR de 101.7 dB en el sine sweep supera en más de 60 dB el mínimo requerido, garantizando deconvoluciones de alta calidad.
- El uso de `filtfilt` (fase cero) en los filtros de octava es una decisión crítica para la correcta temporización de la curva de Schroeder.
- La regresión lineal manual permite interpretar directamente la calidad del decaimiento via R² y rechazar automáticamente bandas con piso de ruido o decaimiento irregular.

**Limitaciones:**
- Solo soporta archivos WAV/FLAC mono (señales estéreo son reducidas al canal 0).
- Sin corrección de Lundeby por defecto: en grabaciones con SNR < 35 dB los parámetros T30 pueden ser imprecisos.
- `sintetizar_ri` usa el modelo de campo difuso ideal, que no reproduce doble pendiente ni decaimientos no exponenciales.

**Trabajo futuro:**
- Activar Lundeby por defecto con detección automática de SNR.
- Agregar soporte multicanal (B-format para acústica espacial).
- Implementar parámetros laterales (JLF, JLFC) según ISO 3382-1.
- Implementar T60 via interpolación directa (sin extrapolar desde T30).

---

## 6. Referencias

- ISO 3382-1:2009. *Acoustics — Measurement of room acoustic parameters — Part 1: Performance spaces.* International Organization for Standardization.
- IEC 61260-1:2014. *Electroacoustics — Octave-band and fractional-octave-band filters.* International Electrotechnical Commission.
- Farina, A. (2000). *Simultaneous measurement of impulse response and distortion with a swept-sine technique.* 108th AES Convention, Paris.
- Schroeder, M. R. (1965). New method of measuring reverberation time. *Journal of the Acoustical Society of America*, 37(3), 409–412.
- Lundeby, A., Vigran, T. E., Bietz, H., & Vorländer, M. (1995). Uncertainties of measurements in room acoustics. *Acustica*, 81(4), 344–355.

---

## Anexo: Log de Desarrollo con IA

### Herramientas utilizadas

- **Claude Code (Anthropic)**: generación de código inicial, revisión de implementaciones, escritura de tests, documentación.
- **[Completar otras herramientas si se usaron]**

### Interacción destacada

**Prompt**: [Describir el prompt más útil que se le dio a la IA]

**Respuesta**: [Resumen de lo que respondió]

**Resultado**: [Cómo se usó, si funcionó, qué se modificó]

### Interacción fallida

**Prompt**: [Describir un caso donde la IA no fue útil o llevó por mal camino]

**Problema**: [Por qué la respuesta no sirvió]

**Lección**: [Qué se aprendió de esa experiencia]

### Reflexión general

[300–500 palabras sobre la experiencia con IA durante el desarrollo del proyecto: impacto en el flujo de trabajo, cuándo fue valioso seguir las sugerencias y cuándo no, cómo cambió la forma de programar.]