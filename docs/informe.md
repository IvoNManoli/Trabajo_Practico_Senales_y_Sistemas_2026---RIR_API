# Informe Técnico — RIR-API
## Señales y Sistemas · UNTREF · 2026

**Integrantes:**
- Ivo Manoli (legajo 64189) — procesamiento de RI
- Gaspar Dallinge (legajo 62751) — testing/CI y documentación

---

## Milestone 1: Generación de Señales

### Objetivo

Implementar las funciones de generación de señales de excitación para mediciones acústicas según ISO 3382: ruido rosa, sine sweep logarítmico con su filtro inverso, y reproducción/grabación simultánea. Estas señales son la entrada del sistema — el sine sweep en particular es el estímulo que permite obtener la RI del recinto mediante deconvolución en M2.

---

## Implementación y decisiones de diseño

### `generar_ruido_rosa`

Genera ruido rosa (ruido 1/f), cuya densidad espectral de potencia es inversamente proporcional a la frecuencia:

$$S(f) = \frac{k}{f}$$

En escala logarítmica esto corresponde a una caída de **−3 dB por octava**, lo que implica igual energía en cada banda de octava.

**Decisión de algoritmo — dominio frecuencial en lugar de Voss-McCartney:**

La consigna admite dos enfoques: el algoritmo Voss-McCartney (dominio temporal) y el filtrado espectral (dominio frecuencial). Se eligió el enfoque frecuencial por ser más directo y controlable:

1. Se genera ruido blanco gaussiano.
2. Se aplica la FFT real (`np.fft.rfft`).
3. Se multiplica cada componente por `1/√f`, que convierte la densidad espectral de plana (blanco) a `1/f` (rosa).
4. Se aplica la FFT inversa (`np.fft.irfft`).
5. Se normaliza el resultado.

La relación entre la pendiente de PSD y el factor de filtrado es: si $S_{blanco}(f) = k$ y se multiplica la amplitud por `1/√f`, la potencia queda multiplicada por `1/f`, resultando en $S_{rosa}(f) = k/f$.

**Decisiones clave:**

- **`rfft`/`irfft` en lugar de `fft`/`ifft`**: Para señales reales, la FFT real es el doble de eficiente porque aprovecha la simetría hermítica del espectro — solo calcula las frecuencias positivas.

- **`factores[0] = 1` (DC sin modificar)**: La componente de continua (f=0) no se filtra para evitar división por cero. En audio la componente DC no tiene relevancia perceptual.

- **`irfft(n=n_muestras)`**: Se pasa explícitamente la longitud deseada para garantizar que la señal de salida tenga exactamente la misma cantidad de samples que la entrada, independientemente de si `n_muestras` es par o impar.

- **Normalización a 0.8 en lugar de 1.0**: Se deja un margen de headroom más amplio que en M2 (donde se usó 0.9) para señales de excitación que van a ser reproducidas por hardware de audio, donde la saturación tiene consecuencias físicas.

---

### `generar_sine_sweep`

Genera un barrido senoidal logarítmico y su filtro inverso, según la técnica de Farina (2000). El sweep es la señal de excitación preferida para medir RIs porque distribuye energía uniformemente por octava y permite separar la RI lineal de las distorsiones armónicas del sistema.

La frecuencia instantánea del sweep crece exponencialmente con el tiempo:

$$f(t) = f_1 \cdot e^{\,t \ln(f_2/f_1)/T}$$

La señal se obtiene integrando la fase:

$$x(t) = \sin\!\left[2\pi f_1 L \left(e^{t/L} - 1\right)\right], \quad L = \frac{T}{\ln(f_2/f_1)}$$

El filtro inverso se construye invirtiendo temporalmente el sweep y aplicando una corrección de amplitud que compensa la distribución no uniforme de energía del sweep logarítmico:

$$x_{\text{inv}}(t) = \frac{x(T-t)}{A(t)}, \quad A(t) = e^{-t \ln(f_2/f_1)/T}$$

Esta corrección es necesaria porque el sweep permanece más tiempo en frecuencias bajas, concentrando más energía ahí. Sin la corrección, la RI resultante tendría más nivel en bajas frecuencias. La relación señal/ruido pico-piso medida para la convolución sweep × filtro inverso fue de **≈ 101.7 dB**, muy por encima del umbral mínimo de 40 dB exigido por el test.

**Decisiones clave:**

- **Sweep logarítmico en lugar de lineal**: El sweep logarítmico invierte igual tiempo en cada octava, distribuyendo la energía de excitación uniformemente en escala logarítmica. Esto es compatible con los filtros de banda IEC 61260 usados en M2 y garantiza buena SNR en todas las bandas de análisis. Un sweep lineal concentraría demasiada energía en altas frecuencias.

- **`endpoint=False` en `np.linspace`**: Evita que la última muestra del sweep sea exactamente `t = T`, lo que provocaría una discontinuidad de fase si la señal se reproduce en loop. Es una práctica estándar para señales periódicas.

- **Headroom de −6 dB (factor 0.5) aplicado al final**: Se reduce la ganancia de ambas señales a la mitad antes de devolverlas. Esto evita clipping durante la reproducción por hardware, donde la señal puede amplificarse antes de llegar al parlante. Se aplica al final para no afectar el diseño matemático del filtro.

- **Misma longitud para sweep y filtro inverso**: Ambas señales tienen exactamente `int(duracion * fs)` muestras. Esto es un requisito implícito de `fftconvolve` en `obtener_ri_desde_sweep` — si tuvieran longitudes distintas el resultado de la deconvolución podría estar desplazado.

---

### `reproducir_y_grabar`

Reproduce una señal por el parlante y graba simultáneamente con el micrófono, usando `sounddevice.playrec`. La grabación debe durar más que la señal reproducida para capturar la cola de reverberación del recinto.

**Decisiones clave:**

- **`sd.playrec` con `blocking=True`**: La función bloquea la ejecución hasta que la reproducción y grabación terminan. La alternativa no bloqueante requeriría manejar callbacks o sincronización manual, aumentando la complejidad sin beneficio en este caso de uso.

- **Padding con ceros hasta `duracion_grabacion`**: Si la señal reproducida es más corta que la duración de grabación, se completa con ceros. Esto permite que el hardware siga grabando la cola de reverberación después de que el estímulo termina, que es el período de interés acústico.

- **Manejo explícito de mono y estéreo**: Se verifica `signal.ndim` y se usa `np.concatenate` para mono o `np.vstack` para estéreo al agregar el padding. Sin esta distinción, el padding tendría la dimensión incorrecta y fallaría en runtime.

- **`.ravel()` en la salida**: `sd.playrec` devuelve siempre un array 2D de shape `(N, channels)`. `.ravel()` lo aplana a 1D, que es el formato que espera el resto del pipeline.

- **Captura de `sd.PortAudioError` específicamente**: En lugar de capturar `Exception` genérico, se captura solo el error de PortAudio, que es el que indica ausencia de dispositivo de audio. Otros errores inesperados se dejan propagar sin silenciarlos.

---

## Tests

### `TestGenerarRuidoRosa`

**`test_ruido_rosa_pendiente_espectral`**
Verifica la pendiente espectral usando FFT directa en lugar del método de Welch que sugería la consigna. Para una señal suficientemente larga (4 segundos), la FFT directa da una estimación confiable y es más simple de implementar que Welch. En escala log-log, la pendiente de la PSD del ruido rosa es −1.0 (la potencia cae como 1/f), que equivale a −3 dB/oct. El test verifica −1.0 con tolerancia de ±0.15, que cubre la varianza estadística inherente al ruido. El rango de frecuencias se limita a 20–15000 Hz para evitar efectos de borde en los extremos del espectro.

---

### `TestGenerarSineSweep`

**`test_convolucion_genera_impulso`**
Verifica que la convolución sweep × filtro inverso produce un impulso con al menos 40 dB de diferencia entre el pico y el piso. Para estimar el piso, se excluyen ±100 samples alrededor del pico — si se incluyeran, el nivel del pico contaminaría la estimación del piso y la relación medida sería artificialmente baja. El umbral de 40 dB es el mínimo práctico para que la deconvolución en M2 produzca una RI útil.

---

### `TestReproducirYGrabar`

**Decisión global: mock de `sd.playrec` y `sd.wait`**
Los tests de audio no pueden correr en CI porque no hay hardware de audio disponible. Se usa `unittest.mock.patch` para reemplazar las llamadas a sounddevice por funciones simuladas. El mock devuelve un array de ceros con shape `(N, 1)`, que es exactamente el formato que devolvería `sd.playrec` en hardware real, garantizando que el test verifica el comportamiento de la función y no el del hardware.

**`test_acepta_senal_mono` y `test_acepta_senal_estereo`**
Verifican que la salida siempre es 1D (`resultado.ndim == 1`) independientemente de si la entrada es mono o estéreo. Esto garantiza que el contrato de la función se cumple y que el pipeline posterior no recibe arrays de dimensión inesperada.

**`test_error_sin_dispositivo`**
Usa `side_effect=sd.PortAudioError(...)` en el mock para simular la ausencia de hardware. Verifica que la función lanza `RuntimeError` con un mensaje específico, en lugar de dejar que el `PortAudioError` interno se propague sin contexto útil.

---

## Validación M1

La validación visual de las señales generadas se realizó comparando los resultados con análisis espectral en Audacity y con los valores teóricos esperados:

| Señal | Criterio | Resultado | Estado |
|---|---|---|---|
| Ruido rosa | Pendiente −3 ± 1 dB/oct | −3.01 dB/oct | ✓ |
| Ruido rosa | Distribución uniforme en el tiempo | Confirmado en espectrograma | ✓ |
| Sine sweep | Barrido monótono 20 Hz → 20 kHz | Confirmado en espectrograma | ✓ |
| Convolución sweep × inverso | SNR pico/piso ≥ 40 dB | ≈ 101.7 dB | ✓ |

---

## Milestone 2: Procesamiento de la Respuesta al Impulso

### Objetivo

Implementar las funciones de procesamiento de la respuesta al impulso (RI): carga de archivos de audio, síntesis de RIs con T60 conocidos por banda, deconvolución mediante sine sweep, filtrado por bandas de octava según IEC 61260, y conversión a escala logarítmica. Estas funciones constituyen la base sobre la que se calcularán los parámetros acústicos ISO 3382 en el Milestone 3.

---

## Implementación y decisiones de diseño

### `cargar_audio`

Carga un archivo de audio WAV o FLAC y devuelve la señal como array NumPy en float64 normalizado entre −1 y 1, junto con la frecuencia de muestreo.

**Decisiones clave:**

- **Librería `soundfile` en lugar de `scipy.io.wavfile`**: `scipy.io.wavfile` solo soporta WAV y devuelve enteros para archivos de 16-bit, requiriendo normalización manual. `soundfile` soporta WAV y FLAC y realiza la conversión y normalización automáticamente con `dtype="float64"`, eliminando una fuente de error.

- **`always_2d=False`**: Para audio mono devuelve shape `(N,)` en lugar de `(N, 1)`. Dado que todas las funciones de procesamiento asumen arrays 1D para señales mono, este parámetro evita tener que hacer squeeze en cada llamada posterior. **Pendiente M3**: el comportamiento ante una señal estéreo no está definido — actualmente la función devuelve ambos canales como shape `(N, 2)` pero ninguna función de procesamiento posterior maneja ese caso. Queda pendiente definir si se promedia a mono, si se toma un canal específico, o si se lanza un error explícito.

- **Verificación explícita de existencia antes de leer**: Verificar `ruta.exists()` antes de llamar a `sf.read` permite lanzar un `FileNotFoundError` con mensaje claro. Sin esta verificación, el error interno de soundfile sería críptico para quien llama a la función.

- **Captura de `Exception` genérico**: `soundfile` puede lanzar distintos tipos de error según el problema (formato inválido, archivo corrupto, permisos). Capturarlos todos y relanzar un único `ValueError` unifica el manejo de errores para las capas superiores.

---

### `sintetizar_ri`

Genera una respuesta al impulso artificial con valores de T60 conocidos por banda de octava. Su propósito principal es proveer una referencia de validación para los algoritmos de análisis del Milestone 3: si se sintetiza una RI con T60 = 2.0 s en 1000 Hz, el algoritmo debería recuperar ese valor.

El modelo matemático es:

$$h(t) = \sum_{\text{banda}} \text{filtro\_octava}(\text{ruido}(t)) \cdot e^{-\alpha t}$$

donde $\alpha = 6.908 / T_{60}$, derivado de la definición de T60 como el tiempo en que la energía decae 60 dB:

$$\alpha = \frac{60}{T_{60} \cdot 20\log_{10}(e)} = \frac{3\ln(10)}{T_{60}} \approx \frac{6.908}{T_{60}}$$

**Justificación del modelo exponencial:**

El decaimiento exponencial corresponde al modelo físico-matemático ideal de la acústica de salas, análogo a fenómenos como la descarga de un capacitor o el decaimiento radiactivo: en cada instante, la energía se pierde a una tasa proporcional a la energía disponible, lo que produce una exponencial como solución.

Este modelo es una aproximación que funciona bien en salas difusas, donde el sonido se distribuye uniformemente en todas las direcciones. En salas con geometría irregular o materiales muy heterogéneos, el decaimiento puede presentar varias pendientes o curvas. Por eso la norma ISO 3382 define parámetros como EDT, T20 y T30 por separado — para detectar cuando el decaimiento no es perfectamente lineal en escala dB.

**Decisiones clave:**

- **Import interno de `filtro_octava`**: El import se ubica dentro de la función en lugar de en el encabezado del módulo para evitar una importación circular. Si `filter.py` importara algo de `signal_utils.py`, el import en el encabezado generaría un loop al cargar los módulos.

- **Ruido blanco filtrado por banda en lugar de exponencial pura**: Una exponencial pura sin ruido no representa el comportamiento de una sala real. El ruido blanco filtrado simula las reflexiones aleatorias que llegan desde todas las direcciones, que es el modelo estándar de campo difuso.

- **Normalización a 0.9 en lugar de 1.0**: Se deja un margen para evitar clipping en procesamiento posterior. Normalizar a exactamente 1.0 podría causar saturación si alguna operación subsiguiente amplifica levemente la señal.

- **Guard `if max_val > 0`**: Evita división por cero en el caso improbable de una RI completamente silenciosa.

---

### `obtener_ri_desde_sweep`

Obtiene la respuesta al impulso de un recinto mediante deconvolución de una grabación de sine sweep. El fundamento matemático es que si el recinto responde $y(t) = x(t) * h(t)$, entonces convolucionando con el filtro inverso se recupera la RI:

$$y(t) * x_{inv}(t) \approx \delta(t) * h(t) = h(t)$$

**Criterio de onset basado en RMS:**

Un aspecto fundamental de esta función es la determinación del punto de inicio de la RI. Recortar exactamente desde el argmax (el pico de mayor amplitud) descarta los primeros samples del ataque del sonido directo, que en una sala real tiene una subida no instantánea. Perder esas muestras afecta directamente el cálculo de parámetros temporales tempranos como el EDT.

Para preservar el ataque, se retrocede desde el pico hasta el primer sample donde la señal emerge del ruido de fondo. El criterio es el siguiente:

1. Se estima el RMS del ruido de fondo usando el último 10% de la señal deconvolucionada, donde la reverberación ya se apagó.
2. Se calcula un umbral de amplitud 20 dB por encima de ese RMS: `umbral = rms_ruido × 10^(20/20) = rms_ruido × 10`.
3. Se retrocede desde el pico muestra a muestra hasta encontrar el primer punto donde la señal cae por debajo de ese umbral — ese es el onset.
4. La RI se recorta desde ese onset hasta el final.

El margen de 20 dB es el valor por defecto elegido por el grupo siguiendo la indicación del profesor de usar un umbral RMS. La norma ISO 3382-1 establece que la RI debe comenzar desde el sonido directo, pero no especifica un umbral numérico concreto para la detección del onset — ese criterio queda a cargo del implementador. El valor de 20 dB es una elección de ingeniería ampliamente utilizada en la práctica, ya que garantiza que el onset esté claramente por encima del ruido sin riesgo de incluir muestras de ruido previas al sonido directo.

Se decidió exponer este valor como parámetro configurable (`margen_db`) para brindar versatilidad a la función: en grabaciones con mayor nivel de ruido de fondo podría ser necesario aumentar el margen, mientras que en condiciones muy limpias un margen menor podría capturar mejor el ataque. Por defecto se utiliza 20 dB, que cubre la mayoría de los casos prácticos.

**Decisiones clave:**

- **`fftconvolve` en lugar de convolución directa**: La convolución directa tiene complejidad O(N²). En el dominio frecuencial con FFT es O(N log N), lo que es decisivo para señales de varios segundos a 44100 Hz.

- **`mode="full"`**: Devuelve el resultado completo de la convolución (longitud N + M − 1). Con `"same"` o `"valid"` se cortaría la cola de reverberación, que es precisamente lo que interesa medir.

- **Estimación del ruido de fondo con el último 10% de la señal**: Al final de la señal deconvolucionada ya se apagó la reverberación y queda solo el ruido de la deconvolución. Es la estimación más limpia disponible sin información externa.

- **Retroceder desde el pico en lugar de buscar hacia adelante desde el inicio**: Buscar desde el inicio podría encontrar falsos positivos — picos de ruido que superen el umbral antes del sonido directo. Retroceder desde el pico garantiza que el onset encontrado pertenece a la región del sonido directo.

- **`margen_db=20.0` configurable**: 20 dB es el margen estándar en acústica para separar señal de ruido. Hacerlo configurable permite ajustarlo según la limpieza de la deconvolución en cada caso.

---

### `filtro_octava`

Aplica un filtro pasabanda de una octava centrado en `fc`, con frecuencias de corte según la norma IEC 61260:

$$f_{inf} = \frac{f_c}{\sqrt{2}}, \quad f_{sup} = f_c \cdot \sqrt{2}$$

**Decisiones clave:**

- **`filtfilt` en lugar de `lfilter`**: `filtfilt` aplica el filtro en dos pasadas (adelante y atrás), cancelando la distorsión de fase. Con `lfilter`, cada componente frecuencial se desplazaría un tiempo distinto, corrompiendo los instantes de llegada de las reflexiones. EDT y T60 dependen de la precisión temporal de la curva de decaimiento, por lo que esta decisión es crítica.

- **Filtro Butterworth en lugar de Chebyshev o elíptico**: El Butterworth tiene respuesta completamente plana en la banda de paso, sin ondulaciones (ripple). Para análisis de decaimiento, todas las frecuencias de la banda deben tener la misma ganancia. Con ripple, algunas frecuencias tendrían más energía que otras y la curva de Schroeder resultaría incorrecta.

- **`min(f_sup / nyq, 0.9999)` para la frecuencia de corte superior**: En bandas altas (ej. 8000 Hz o 16000 Hz a 44100 Hz de muestreo), la frecuencia de corte superior puede superar Nyquist. `butter` no acepta valores ≥ 1.0 en frecuencia normalizada — clampear a 0.9999 evita el error sin alterar significativamente el comportamiento del filtro.

- **Orden 4 por defecto**: Es un balance entre selectividad y estabilidad numérica. Órdenes más altos dan una caída más pronunciada fuera de banda pero `filtfilt` puede volverse inestable para filtros de orden muy alto.

---

### `a_escala_log`

Convierte una señal de amplitud lineal a decibeles normalizados, con 0 dB en el pico y piso en −120 dB:

$$L(t) = 20 \cdot \log_{10}\left(\frac{|h(t)|}{\max|h|}\right)$$

**Decisiones clave:**

- **Aplicar el piso de −120 dB antes del logaritmo, no después**: Si se aplicara después, se calcularía `log10(0) = -inf` en el paso intermedio, generando `NaN` o `-inf` que pueden propagar errores silenciosamente. Aplicándolo antes (como valor mínimo de `ratio`), nunca se llama a `log10` con 0.

- **Piso en −120 dB en lugar de `np.finfo(float).eps`**: `eps` (~2.2e-16) daría un piso de ~−315 dB, sin sentido físico. −120 dB corresponde al límite práctico del rango dinámico en mediciones acústicas reales.

- **Normalizar con `np.abs` antes de buscar el máximo**: Una RI tiene valores positivos y negativos. Sin valor absoluto, si el pico negativo fuera mayor en magnitud que el positivo, la normalización sería incorrecta.

---

## Tests

### Estrategia general de testing

Los tests siguen una estructura de caja negra: se proveen entradas conocidas, se llama a la función y se verifica que la salida cumpla las propiedades esperadas. En ningún caso se accede a los internos de las funciones. Esto permite refactorizar la implementación sin romper los tests.

---

### `TestCargarAudio`

**`test_cargar_audio_no_existe`**
Verifica que la función falla correctamente cuando el archivo no existe. Se prioriza este test porque una función que falla con un error críptico en producción es peor que una que no existe.

**`test_cargar_audio_wav`**
Usa `subtype="FLOAT"` al escribir el archivo de prueba en lugar del WAV por defecto (16-bit entero). Con 16-bit la cuantización introduce error suficiente para que `assert_allclose` falle aunque la función sea correcta. El `try/finally` garantiza que el archivo temporal se borre incluso si el test falla a mitad.

**`test_cargar_audio_formato_invalido`**
Usa un archivo con extensión `.wav` pero contenido basura, en lugar de una extensión inválida como `.xyz`. Simula el caso real de un usuario que sube un archivo mal formado o renombrado. Con extensión inválida, `soundfile` podría rechazarlo antes de ejercitar el código de manejo de errores interno.

**`test_cargar_audio_normalizacion`**
Verifica la propiedad de normalización con tolerancia `1e-6` para cubrir errores de punto flotante.

---

### `TestAEscalaLog`

**`test_a_escala_log_valores`**
No usa `assert db[0] == 0.0` sino `assert abs(db[0] - 0.0) < 1e-10`. Las operaciones de punto flotante introducen errores numéricos pequeños y la igualdad exacta puede fallar aunque la función sea correcta.

---

### `TestSintetizarRI`

**`test_sintetizar_ri_decaimiento`**
Fija `np.random.seed(42)` antes de generar el ruido. Sin semilla, el ruido cambia en cada corrida y el T60 medido puede variar lo suficiente para fallar el assert en algunas ejecuciones. La semilla hace el test determinístico.

Usa la integral de Schroeder para medir el T60 en lugar de medir directamente el decaimiento de amplitud. La integral de Schroeder es el método estándar ISO 3382 y es más robusta al ruido que medir la envolvente directamente.

La tolerancia del 10% es la que la propia norma ISO 3382 considera aceptable para la varianza estadística inherente al modelo de campo difuso.

---

### `TestFiltroOctava`

**`test_filtro_octava_frecuencia_central`**
Excluye el primer y último 10% del array para calcular el RMS. `filtfilt` genera transitorios en los bordes por la naturaleza finita de la señal. Incluir esos bordes bajaría artificialmente el RMS de salida y haría fallar el test aunque el filtro funcione correctamente.

Usa senoidal pura en lugar de ruido blanco. Con ruido blanco, la energía fuera de la banda sería atenuada por el filtro, bajando el RMS de salida incluso si la frecuencia central pasa bien. La senoidal pura a `fc` aísla exactamente la frecuencia que se quiere verificar.

**`test_filtro_octava_atenuacion`**
Elige `fc/2` y `fc*2` (una octava fuera de la banda) como frecuencias de prueba. Son el caso más exigente — las frecuencias más cercanas a la banda de paso. Con frecuencias más lejanas el test sería trivial de pasar y no verificaría el diseño real del filtro.

**`test_filtro_octava_respuesta_frecuencia`**
Usa `freqz` en lugar de filtrar señales reales y medir RMS. `freqz` evalúa la respuesta del filtro analíticamente en exactamente las frecuencias de interés. Con señales reales habría error de estimación y transitorios de borde que dificultarían verificar los −3 dB exactos que define la norma IEC 61260.

---

### `TestObtenerRIDesdeSweep`

**`test_obtener_ri_pico`**
Usa una senoidal con decaimiento exponencial en lugar de `sintetizar_ri`. `sintetizar_ri` introduce ruido aleatorio y depende de `filtro_octava` internamente. Si el test fallara, no se sabría si el problema está en `obtener_ri_desde_sweep` o en `sintetizar_ri`. La senoidal es determinística y no tiene dependencias externas, aislando la función que se quiere probar.

Usa correlación cruzada normalizada en lugar de comparación sample a sample. La deconvolución puede introducir un pequeño desfase temporal entre la RI original y la recuperada. La correlación cruzada encuentra el mejor alineamiento posible antes de comparar, evitando fallos por desplazamientos de pocos samples que no afectan la calidad de la RI.

El umbral de 0.9 en lugar de 1.0 reconoce que la deconvolución no es perfecta y hay pequeñas diferencias numéricas inevitables. 0.9 verifica que la forma de la RI es correcta sin exigir una precisión inalcanzable.
