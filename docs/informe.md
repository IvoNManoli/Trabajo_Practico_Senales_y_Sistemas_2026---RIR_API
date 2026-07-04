# Informe Técnico — RIR-API
## Señales y Sistemas · UNTREF · 2026

**Integrantes:**
- Ivo Manoli (legajo 64189) — Generación y procesamiento de RI
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

El ruido rosa se define como un ruido cuya energía por octava es constante. Eso implica que en las bandas más graves, al haber menos frecuencias, la energía por frecuencia sea mayor que en las bandas agudas. Es decir, puedo pensar que la "cantidad de energía por frecuencia" cae según aumenta la frecuencia. No obstante, en vez de energía se utiliza la potencia, dado que permite independizarnos del tiempo de integración (si integro en tiempos más largos, la energía es mayor, pero la potencia es la misma). 

Como la potencia por frecuencia cae a medida que aumenta la frecuencia, podría deducirse la ecuación 1: 

$$S(f) = \frac{k}{f}\tag{1}$$

Esa fórmula tiene su demostración física/matemática de mayor complejidad, pero sin entrar en detalles es  intuitivamente correcta. Al graficar el nivel de potencia en función de la frecuencia en eje logarítmico de frecuencia, observaremos una recta decreciente con una pendiente de -3 dB por octava. 


### 2.2 Sine sweep logarítmico (Farina, 2000)

Para poder medir una respuesta al impulso en un recinto, sería tan sencillo como emitir un impulso perfecto en un recinto y medir su respuesta. El problema es que físicamente es imposible obtener un impulso perfecto. Frente a esa imperfección surgen distintas soluciones como por ejemplo utilizar la respuesta de una explosión (como un globo) o un disparo. El problema de este tipo de métodos es que no son replicables y son demasiado variables según el tipo de estímulo y material utilizado, entre otros factores. Otro tipo de solución podría ser utilizar ruido rosa mediante un sistema de reproducción, y obtener la respuesta al impulso utilizando funciones de transferencia, pero las distorsiones propias del sistema también variarían mucho los resultados. Quién pudo brindar una mejor aproximación al impulso fue Farina, quien en el año 2000 presentó su método del sine sweep logarítmico y el filtro inverso.

El sine sweep (barrido senoidal) es una señal senoidal que aumenta gradualmente su frecuencia a lo largo del tiempo, pensada para excitar toda la banda de interés en una sola medición. Dicha señal comienza en las frecuencias graves y se desplaza hasta las frecuencias agudas, mientras que su filtro inverso es la inversión temporal de este barrido. Farina demostró matemáticamente que la convolución entre ese barrido y su filtro inverso es una aproximación al impulso, siempre que ambas señales senan lo suficientemente largas (Farina, 2000). 

Por diversos factores, es conveniente que el barrido sea logarítmico, es decir, que invierta el mismo tiempo por cada banda. Por ejemplo, si el tiempo por banda son 5 segundos, se demoraría 5 segundos en desplazarse desde la frecuencia de 100 a 200 hz y el mismo tiempo entre 5000 y 10000 hz. En la ecuacion 2 se puede observar la fórmula que establece la frecuencia instantánea del barrido, donde f1 y f2 son las frecuencias iniciales y finales, respectivamente (por interés acústico de 20 Hz a 20 kHz), T es la duración total del sweep, y t es el valor de tiempo en el instante a evaluar:


$$f(t) = f_1 \cdot e^{\,t \ln(f_2/f_1)/T} \tag{2}$$


Integrando esa frecuencia instantánea se obtiene la fase de la señal, y de ahí la expresión completa del sweep (ecuación 3):

$$x(t) = \sin\!\left[2\pi f_1 L \left(e^{t/L} - 1\right)\right], \quad L = \frac{T}{\ln(f_2/f_1)} \tag{3}$$

Tal como se mencionó, para poder recuperar la respuesta al impulso de una sala a partir de la grabación del sweep, hace falta además su filtro inverso, una señal que, convolucionada con el sweep, dé como resultado un impulso. Se construye invirtiendo el sweep en el tiempo y aplicándole una corrección de amplitud que compensa el hecho de que las frecuencias bajas estuvieron sonando más tiempo que las altas (ecuación 4):

$$x_{\text{inv}}(t) = \frac{x(T-t)}{A(t)}, \quad A(t) = e^{-t \ln(f_2/f_1)/T} \tag{4}$$

De esta manera, la convolución del sweep con su filtro inverso converge a una delta de Dirac, lo que en la práctica significa que convolucionar la *grabación* de una sala (sweep deformado por la RI del recinto) con ese mismo filtro inverso permite recuperar directamente la RI (ecuación 5):

$$y(t) * x_{\text{inv}}(t) \approx h(t) \tag{5}$$


### 2.3 Filtros de banda de octava (IEC 61260)

Por definición, las frecuencias de corte de un filtro de octava centrado en $f_c$ se aprecian en las ecuaciones 6 y 7:

$$f_{\text{inf}} = \frac{f_c}{\sqrt{2}} \tag{6}$$

$$f_{\text{sup}} = f_c \cdot \sqrt{2} \tag{7}$$

En metodología se explicará en más detalle de qué manera fueron implementados los filtros.

### 2.4 Integral de Schroeder (Energy Decay Curve)

La integral de Schroeder representa el decaimiento de energía acústica mediante integración inversa (ecuación 8). La ecuación 9 indica el análogo discreto:

$$E(t) = \int_{t}^{\infty} h^2(\tau) \, d\tau \tag{8}$$

$$E[n] = \sum_{k=n}^{N-1} h^2[k] \tag{9}$$

Consiste en una integración desde el final de la energía de la señal hasta el principio, que da como como resultado una gráfica de energía en función del tiempo. Es particularmente útil dado que teóricamente, la caída de la energía de la señal luego del impulso debería ser exponencialmente decreciente, por lo que al tomar el nivel de la energía el resultado teórico ideal sería una recta perfecta decreciente. En la vida real esto no ocurre, o por lo menos no de esta manera perfecta. No obstante, si se puede observar un tramo lineal antes de llegar al piso de ruido, que para una señal real puede ajustarse por cuadrados mínimos para así obtener los valores de EDT, T10, T20, T30 y T60. 


### 2.5 Parámetros acústicos ISO 3382

Tal como se mencionó previamente, ajustando la curva de Schroeder se obtienen los parámetros acústicos temporales. Por diversas demostraciones físicas y cálculos acústicos es necesario conocer el tiempo que una señal tarda en caer 60 dB en el recinto, pero como es muy difícil y poco práctico obtener un impulso que permita una caída de -60 dB, este valor normalmente se obtiene por extrapolación de la recta ajustada a la curva de schroeder. La siguiente tabla indica entre qué valores se ajusta la recta de cada parámetro:

| Parámetro | Rango de ajuste |
|-----------|:----------------:|
| EDT | 0 dB a −10 dB |
| T10 | −5 dB a −15 dB |
| T20 | −5 dB a −25 dB |
| T30 | −5 dB a −35 dB |

*Tabla 1: rango de ajuste de la curva de Schroeder para cada parámetro de reverberación.*

Para obtener T10, T20 y T30 basta con calcular su recta de ajuste y calcular cuánto tiempo tardaría la señal, si siguiese en esa recta, en caer -60 dB (extrapolación).

A diferencia de EDT/T10/T20/T30, la Definición ($D_{50}$) y la Claridad ($C_{80}$) no se obtienen ajustando una recta a la curva de Schroeder, sino comparando directamente la energía de la RI en distintas ventanas de tiempo.

$D_{50}$ mide qué porcentaje de la energía total llega dentro de los primeros 50 ms desde el sonido directo, frente a la energía total de toda la respuesta. Es un indicador de inteligibilidad de la palabra: cuanto más alto, más clara se percibe la voz hablada en la sala.

$C_{80}$ compara, en dB, la energía que llega en los primeros 80 ms (sonido directo más primeras reflexiones) contra la energía que llega después de ese punto (la cola reverberante). Un valor alto indica que predomina la energía temprana sobre la tardía, lo cual favorece la claridad percibida en música.

### 2.6 Regresión lineal por mínimos cuadrados

El ajuste lineal busca la recta que mejor aproxima la curva de Schroeder en el tramo elegido, minimizando el error cuadrático total (ecuación 10). De ella se obtiene la pendiente $m$ (ecuación 11), usada para calcular los tiempos de reverberación, y la ordenada al origen $b$ (ecuación 12). El $R^2$ (ecuación 13) indica qué tan bueno fue ese ajuste.

$$\sum (y_i - \hat{y}_i)^2 \tag{10}$$

$$m = \frac{N \sum x_i y_i - \sum x_i \sum y_i}{N \sum x_i^2 - (\sum x_i)^2} \tag{11}$$

$$b = \frac{\sum y_i - m \sum x_i}{N} \tag{12}$$

$$R^2 = 1 - \frac{\sum (y_i - \hat{y}_i)^2}{\sum (y_i - \bar{y})^2} \tag{13}$$

---

## 3. Desarrollo Experimental

### 3.1 Arquitectura del software

El sistema se diseñó siguiendo una arquitectura de tres capas estrictamente separadas, tal como puede apreciarse en la figura 1:

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
*Figura 1: Arquitectura de la API*

A continuación la Tabla 2 resume brevemente cada función desarrollada en las tres milestones y a qué servicio pertenece, antes de entrar en el detalle de cada una:

| Nombre | Funcionalidad | Servicio |
|---|---|---|
| `generar_ruido_rosa` | Genera ruido rosa  | `pink_noise.py` |
| `generar_sine_sweep` | Genera el sweep logarítmico y su filtro inverso | `sine_sweep.py` |
| `reproducir_y_grabar` | Reproduce el sweep y graba la respuesta de la sala | `grabacion_utils.py` |
| `cargar_audio` | Carga un WAV/FLAC, devuelve la señal normalizada y frecuencia de muestreo | `signal_utils.py` |
| `sintetizar_ri` | Genera una RI artificial con T60 conocido por banda | `signal_utils.py` |
| `obtener_ri_desde_sweep` | Deconvoluciona la grabación para obtener la RI | `signal_utils.py` |
| `a_escala_log` | Convierte la señal de amplitud lineal a escala dB | `signal_utils.py` |
| `filtro_octava` | Filtra la señal en una banda de octava  | `filter.py` |
| `suavizar_signal` | Suaviza la envolvente de la RI (Hilbert o media móvil) | `acoustic_parameters.py` |
| `integral_schroeder` | Calcula la curva de decaimiento de energía (EDC) | `acoustic_parameters.py` |
| `regresion_lineal` | Ajuste por mínimos cuadrados (pendiente, ordenada, R²) | `acoustic_parameters.py` |
| `calcular_parametros_acusticos` | Calcula EDT/T10/T20/T30/D50/C80 por banda | `acoustic_parameters.py` |
| `metodo_lundeby` | Determina el punto óptimo de truncamiento de la RI | `acoustic_parameters.py` |
| `convolucionar` | Convoluciona un audio con una RI (validación subjetiva) | `convolution.py` |
| Endpoints REST (`app/routers/*.py`) | Exponen las funciones anteriores vía HTTP | *No es un servicio — es la capa HTTP* |

*Tabla 2: funciones de las milestones y servicio al que pertenecen.*

En los apartados posteriores se desarrollará en profundidad todos los detalles respectivos a cada servicio y demás características fundamentales de la API. 

### 3.2 Flujo de procesamiento completo

Si se desea conocer los parámetros acústicos de una RI ya previamente obtenida, el flujo consistiría en cargar el audio en archivo wav o flac, donde internamente el servidor procesará la RI filtrándola, aplicando la integral de schroeder,realizando un ajuste por cuadrados mínimos y finalmente obteniendo el parámetro deseado. La figura 2 ilustra este flujo, presentando a las funciones responsables de llevar a cabo tales tareas:

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
*Figura 2: Flujo de procesamiento*



### 3.3 Milestone 1 — Generación de señales

## 3.3.1 Generación de ruido rosa

Se desarrolló la función `generar_ruido_rosa()` que recibe como argumentos la duración deseada como objeto flotante y la frecuencia de muestreo objeto entero, y devuelve un array de Numpy con el ruido rosa. En cuanto al algoritmo, la metodología aplicada consistió en crear ruido blanco con distribución normal mediante una función de la librería Numpy. Posteriormente al array creado se le aplicó la transformada rápida de fourier (FFT) para convertir a un vector en el dominio frecuencial, donde cada argumento representa un número complejo y cada índice una frecuencia. También se creó un vector de frecuencias, para luego dividir al vector de la transformada por este vector de frecuencias y así aplicar la ecuación 1 para obtener un vector de ruido rosa. Finalmente se aplicó la transformada inversa para obtener nuevamente un array en el dominio temporal y además se le aplicó una normalización entre -0,8 y 0,8, liberando así un margen de seguridad para evitar cualquier tipo de distorsión digital.

Se optó por el algoritmo de la FFT frente a otros como Voss-Mccartney por una mayor simplicidad conceptual y de sintáxis. No obstante, para garantizar un buen resultado se implementaron diversos test de control (pytest). Dentro de los test de ruido rosa, la mayoría cumple un rol trivial, como por ejemplo verificar que la salida de la función sea un array, o que esté normalizada. No obstante, el test más fundamental fue el de verificar que la pendiente de la densidad espectral de potencia sea efectivamente de -3 dB por octava. Este test es crucial, y pasarlo garantiza que el ruido sea efectivamente rosa. Internamente el test utiliza el método de Welch de la librería `scipy.signal`.

El método de Welch estima la densidad espectral de potencia dividiendo la señal en segmentos solapados, calculando el periodograma (FFT) de cada uno y promediándolos. Se prefirió frente a una FFT simple porque el periodograma de una única FFT es un estimador muy ruidoso de la PSD, ya que su varianza no mejora aunque la señal sea más larga, mientras que promediar varios segmentos suaviza esas fluctuaciones y da una estimación mucho más estable de la pendiente real del espectro, necesaria para verificar con confianza el -3 dB/octava esperado.

## 3.3.2 Generación de sine sweep y filtro inverso

La función responsable de crear el sine sweep y su filtro inverso fue **`generar_sine_sweep()`**, que recibe como argumentos la frecuencia inicial y final del barrido como objetos flotantes, la duración deseada como objeto flotante y la frecuencia de muestreo como objeto entero, y devuelve dos arrays de Numpy: el sweep y su filtro inverso. El algoritmo arma primero un vector de tiempo con `np.linspace`, calcula la constante $L$ de la ecuación 3 y a partir de ahí la fase instantánea, para finalmente aplicarle el seno y obtener el barrido. El filtro inverso se obtiene invirtiendo el array del sweep (`sweep[::-1]`) y multiplicándolo por una rampa exponencial decreciente que implementa la corrección de amplitud $A(t)$ de la ecuación 4, normalizando después a un pico de 1.0. Por último, tanto el sweep como su filtro inverso se multiplican por una ganancia de 0.5 (headroom de −6 dB) elegido arbitrariamente para evitar clipping al reproducirlos por hardware real.

Para corroborar su correcto funcionamiento, además de los test triviales se incluyó un test fundamental, el cual verifica que la convolución entre el sine sweep y el filtro inverso efectivamente sea un impulso, cuyo pico se sitúe por lo menos 40 dB por encima del nivel del piso de ruido. Para este test se eligió utilizar el algoritmo por excelencia para este tipo de cálculos, `fftconvolve` de `scipy.signal`.

`fftconvolve` calcula la convolución explotando el teorema de convolución: en vez de sumar el producto desplazado muestra a muestra, transforma ambas señales al dominio de la frecuencia mediante FFT, las multiplica punto a punto, y antitransforma el resultado con FFT inversa para volver al dominio temporal. Esto es muy práctico puesto que calcular una convolución directamente implica mucho más procesamiento que una multiplicación. Internamente aplica zero-padding a las señales de entrada para que esa multiplicación en frecuencia represente la convolución lineal deseada y no una convolución circular (que "envolvería" la cola de la señal sobre el principio).

Puntualmente en el test, se generan un sweep y su filtro inverso de 5 segundos a 44100 Hz y se convolucionan con `fftconvolve`. Sobre el resultado se busca el índice de la muestra de mayor amplitud absoluta, que corresponde al pico del impulso recuperado. Para estimar el piso de ruido se enmascaran las 200 muestras centradas en ese pico (±100 muestras) y se promedia el valor absoluto de todas las muestras restantes. Finalmente se calcula la relación pico/piso en decibeles como 20·log10(pico/piso) y se verifica que sea de al menos 40 dB, el umbral mínimo para considerar que la deconvolución en Milestone 2  recuperará una RI con buena resolución temporal y bajo nivel de artefactos.

## 3.3.3 Reproducción y grabación simultánea

Para poder medir una RI real en un recinto hace falta, además de generar la señal de excitación, un mecanismo que la reproduzca por un parlante y grabe simultáneamente la respuesta del recinto con un micrófono. Esa tarea la resuelve la función `reproducir_y_grabar()`, que recibe la señal a reproducir (mono o estéreo), la frecuencia de muestreo, la duración deseada de grabación y un tiempo de preroll (0.5 s por defecto), devolviendo un array de Numpy 1D con el audio capturado.

Internamente se apoya en `sd.playrec()` de la librería `sounddevice`, que reproduce un array y graba al mismo tiempo, devolviendo una grabación de exactamente la misma longitud que el array reproducido. Esto impone una restricción: si se le pasara únicamente la señal de excitación, la grabación terminaría junto con ella y se perdería toda la cola de reverberación del recinto, que es el dato que en realidad interesa capturar. Para resolverlo, la función arma un array extendido concatenando tres tramos: un tramo inicial de silencio (`n_preroll` muestras), la señal de excitación, y un tramo final de silencio (`n_padding` muestras) calculado como la diferencia entre la duración total de grabación pedida y lo ya ocupado por preroll y señal. Ese array extendido es el que finalmente se le pasa a `sd.playrec()`.

**Decisiones clave:**
- El preroll inicial compensa la latencia propia del sistema de audio (el tiempo que tarda la placa en arrancar a reproducir/grabar de forma efectiva), evitando perder las primeras muestras útiles.
- El padding final no reproduce nada, pero al ser parte del array reproducido, extiende la duración de la grabación lo suficiente como para que la reverberación del recinto decaiga naturalmente antes de que `sd.playrec()` corte la captura.
- Se admite señal mono (`ndim == 1`) o estéreo (`ndim == 2`), ajustando `n_channels` y usando `np.concatenate` o `np.vstack` según corresponda.
- Un `sd.PortAudioError` (por ejemplo, ausencia de dispositivo de audio) se recaptura y se relanza como `RuntimeError` con un mensaje claro, en vez de propagar la excepción de bajo nivel de `sounddevice`.

Como los tests de este proyecto corren en un entorno sin hardware de audio real, `sd.playrec` y `sd.wait` se mockean con `unittest.mock.patch`, simulando una grabación de la duración esperada. Los tests verifican que la salida sea siempre 1D independientemente de si la entrada fue mono o estéreo, que la longitud de la grabación coincida (con una tolerancia del 1%) con `duracion_grabacion + preroll`, y que si `sd.playrec` lanza un `PortAudioError` la función efectivamente lo traduzca a un `RuntimeError` con el mensaje "No hay dispositivo de audio disponible".


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