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

Internamente se apoya en `sd.playrec()` de la librería `sounddevice`, que reproduce un array y graba al mismo tiempo, devolviendo una grabación de exactamente la misma longitud que el array reproducido. Esto impone una restricción: si se le pasara únicamente la señal de excitación, la grabación terminaría junto con ella y se perdería toda la cola de reverberación del recinto, que es el dato que en realidad interesa capturar. Para resolverlo, la función arma un array extendido concatenando tres tramos: un tramo inicial de silencio ("n_preroll" muestras), la señal de excitación, y un tramo final de silencio ("n_padding" muestras) calculado como la diferencia entre la duración total de grabación pedida y lo ya ocupado por preroll y señal. Ese array extendido es el que finalmente se le pasa a `sd.playrec()`.

El preroll inicial compensa la latencia propia del sistema de audio (el tiempo que tarda la placa en arrancar a reproducir/grabar de forma efectiva), evitando perder las primeras muestras útiles. Por otro lado, el padding final no reproduce nada, pero al ser parte del array reproducido, extiende la duración de la grabación lo suficiente como para que la reverberación del recinto decaiga naturalmente antes de que `sd.playrec()` corte la captura.
Se admite señal de excitación mono o estéreo (por ejemplo un sweep reproducido por dos parlantes), usando `np.concatenate` o `np.vstack` de la librería `numpy` según corresponda para armar el array extendido.

La grabación, en cambio, es siempre mono. Esta decisión fue tomada debido a que para todo el procesamiento de respuestas al impulso es necesario ingresar señales mono. El parámetro "channels" que se le pasa a `sd.playrec()` está fijo en 1, independientemente de cuántos canales tenga la señal reproducida. 

En caso de error por no conectar ningún dispositivo de audio, `sd.PortAudioError` se recaptura y se relanza como `RuntimeError` con un mensaje claro, en vez de propagar la excepción de bajo nivel de `sounddevice`.

Como los tests de este proyecto corren en un entorno sin hardware de audio real, `sd.playrec` y `sd.wait` se mockean con `unittest.mock.patch`, simulando una grabación de la duración esperada. Los tests verifican que la salida sea siempre 1D independientemente de si la señal reproducida fue mono o estéreo, que en ambos casos `sd.playrec` se llame con `channels=1`, que la longitud de la grabación coincida (con una tolerancia del 1%) con `duracion_grabacion + preroll`, y que si `sd.playrec` lanza un `PortAudioError` la función efectivamente lo traduzca a un `RuntimeError` con el mensaje "No hay dispositivo de audio disponible".

Los test fundamentales de esta función incluyen a  `test_acepta_senal_mono` , la cual pasa una señal 1D, verifica que el resultado sea un array 1D y que `sd.playrec` se haya llamado con "channels=1". Luego `test_acepta_senal_estereo` ,que pasa una señal 2D de dos canales y comprueba tanto que la grabación siga siendo mono (channels=1) como que el array efectivamente reproducido haya conservado sus dos columnas, es decir, que el armado del preroll y el padding no haya roto la forma de la señal de salida. Uno de los más fundamentales es `test_duracion_correcta`, quien verifica que la longitud de la grabación devuelta coincida, con una tolerancia del 1%, con la duración pedida más el preroll. Por último, `test_error_sin_dispositivo` simula un `sd.PortAudioError` y confirma que la función lo traduce en un "RuntimeError" con un mensaje claro en vez de propagar la excepción de bajo nivel.

Un aspecto fundamental de esta función es que no se incluye como servicio de la API. Esto es debido a que el acceso del servidor al micrófono y los parlantes del cliente requiere de ser informado y debe solicitar los permisos adecuados para hacerlo. Si el software pudiese acceder sin permisos se trataría de un malware, lo cual claramente no es la intención del proyecto. Dado que el correcto abordaje de esta temática es un tema de desconocimiento de los autores, se decidió limitar la ejecución de esta función vía script. 

### 3.4 Milestone 2 — Procesamiento de la RI

## 3.4.1 Carga de audio y respuesta al impulso

A la hora de analizar una respuesta al impulso es necesario brindar un servicio que permita cargar el audio al servidor. Esa es la función de `cargar_audio()`, que recibe una ruta a un archivo (para ejecutarlo vía script) o directamente un objeto file-like, y devuelve una tupla con la señal como array de Numpy en float64 y su frecuencia de muestreo. Internamente usa `soundfile.read()` para soportar tanto WAV como FLAC en un único llamado, que ya se encarga de la conversión de formato y de dejar la señal en punto flotante. Antes de leer, si la entrada es una ruta en disco se verifica explícitamente que el archivo exista, lanzando un "FileNotFoundError" con un mensaje claro en vez de dejar que falle más abajo con un error críptico de la librería; cualquier otro problema de lectura (formato no soportado, archivo corrupto) se recaptura como "ValueError". Finalmente, la señal se normaliza dividiendo por su valor absoluto máximo y escalando a 0.9.

Dado que el procesamiento de RI requiere señales mono, si el archivo cargado es estéreo (o multicanal), la función extrae un único canal antes de normalizar, devolviendo siempre un array 1D. Cuál canal extraer es un parámetro de la función, que acepta "L", "R" o directamente un índice entero de canal (por defecto L); si se pide un canal que no existe, se lanza un ValueError. Esto es necesario porque el resto del pipeline de procesamiento está diseñado para trabajar sobre una única señal temporal, no sobre un array con un eje de canales.

Un objeto file-like ("similar a un archivo") es cualquier objeto de Python que se comporta como un archivo abierto en disco sin serlo necesariamente, aunque los datos vivan en otro lado, por ejemplo en memoria. El caso típico acá es "io.BytesIO", que envuelve bytes ya cargados en RAM, como el contenido de un archivo subido a la API para que pueda leerse con la misma interfaz que un archivo real. Se decidió hacer esto para permitir a la función aceptar tanto una ruta en disco como el contenido de un upload HTTP sin necesidad de guardarlo primero a un archivo temporal.

Esta función cuenta con siete tests. Se verifica que una ruta inexistente lance FileNotFoundError; que la carga básica de un WAV mono funcione correctamente, chequeando forma, frecuencia de muestreo y normalización; que un archivo corrupto (bytes que no son audio) se traduzca en un ValueError; y que la señal devuelta quede siempre dentro de −1 y 1. Los tres restantes cubren la selección de canal: que, sin especificar nada, un archivo estéreo devuelva el canal L por defecto; que pasando explícitamente el canal "R" se obtenga el canal derecho; y que pedir un canal inexistente (por nombre o por índice fuera de rango) lance ValueError.

## 3.4.2 Filtro de banda de octava

Para conocer los parámetros acústicos no basta con un índice global en todas las frecuencias, dado que el comportamiento en cada frecuencia es crucial para el análisis acústico. Es por eso que los software de medición de parámetros acústicos reportan sus datos en bandas. En este caso la API cuenta con un filtro únicamente de ancho de banda de octava. Esa es la finalidad de la función `filtro_octava()`, que recibe como entrada a la señal, las frecuencias centrales de las bandas deseadas, la frecuencia de muestreo y el orden del filtro Butterworth (por defecto 4).

Un filtro Butterworth es un tipo de filtro analógico/digital cuya característica distintiva es tener una respuesta en magnitud maximalmente plana, es decir, dentro de la banda de paso. No presenta ripple (ondulaciones) ni en la banda de paso ni en la de rechazo, a diferencia de otras familias como Chebyshev (que tolera ripple en la banda de paso o de rechazo a cambio de una caída más abrupta) o el elíptico (que tiene ripple en ambas bandas, pero la transición más pronunciada de todas para un mismo orden). Esa planicie tiene un costo: para una misma pendiente de caída, un Butterworth necesita mayor orden que un Chebyshev o un elíptico. Otra propiedad importante es que, por definición matemática, su magnitud cae exactamente a −3 dB en la frecuencia de corte, sin importar el orden del filtro, una referencia útil para verificar que el filtro esté bien diseñado.

La ventaja de utilizar específicamente un filtro Butterworth, y no Chebyshev o elíptico en el contexto de medición de parámetros acústicos, es por la ausencia de ripple en la banda de paso.Si el filtro tuviera ondulaciones, algunas frecuencias dentro de la misma banda de octava quedarían con más o menos energía que otras de forma artificial, y como los parámetros acústicos se calculan a partir de la energía de la señal filtrada, cualquier ripple se traduciría directamente en un sesgo en esos cálculos. La respuesta plana del Butterworth garantiza que, dentro de la banda, todas las frecuencias se atenúen (o dejen pasar) de manera uniforme, preservando la relación de energía real de la señal en esa banda — algo más importante acá que lograr una transición más abrupta entre bandas.

Puntualmente, `filtro_octava()` calcula primero las frecuencias de corte inferior y superior de la banda, las normaliza respecto de la frecuencia de Nyquist, y con eso diseña un filtro pasabanda Butterworth mediante `scipy.signal.butter(orden, wn, btype="band", output="sos")`. Lo aplica con `sosfiltfilt` para obtener fase cero, evitando la distorsión de fase que introduciría un filtrado en una sola dirección.

Esta función cuenta con tres tests. El primero verifica que una senoidal exactamente en la frecuencia central de la banda pase prácticamente sin atenuación (ganancia menor a 1 dB), comparando el RMS de la señal antes y después de filtrar. El segundo comprueba lo contrario: senoidales a la mitad y al doble de la frecuencia central (es decir, fuera de la banda de octava) deben atenuarse más de 20 dB. El tercero valida la respuesta en frecuencia del filtro contra la definición teórica de una banda de octava: calcula la respuesta con `scipy.signal.freqz` y confirma que la ganancia sea máxima (~0 dB) en la frecuencia central, y de exactamente −3 dB en ambas frecuencias de corte.

## 3.4.3 Síntesis de respuesta al impulso artificial

Para validar los cálculos de los parámetros acústicos resulta conveiniente generar una RI cuyo T60 real ya se conozca de antemano, algo que no se puede garantizar con una RI medida en un recinto real. Ese es el propósito de `sintetizar_ri()`: recibe un diccionario `{frecuencia_central: T60}` por banda, la frecuencia de muestreo y la duración deseada, y devuelve una respuesta al impulso artificial que decae exactamente con esos T60 conocidos, banda por banda.

El modelo utilizado es ruido blanco filtrado por banda multiplicado por una envolvente exponencial decreciente, sumado entre todas las bandas del diccionario (ecuación 14):

$$h(t) = \sum_{\text{banda}} \text{filtro\_octava}(\text{ruido}(t)) \cdot e^{-\alpha t}, \quad \alpha = \frac{6.908}{T_{60}} \tag{14}$$

El coeficiente $\alpha$ se deriva directamente de la definición de T60 como el tiempo en que la energía cae 60 dB (ecuación 15):

$$\alpha = \frac{3\ln(10)}{T_{60}} \approx \frac{6.908}{T_{60}} \tag{15}$$

La razón por la cuál se genera ruido blanco independiente para cada banda y se lo filtra con `filtro_octava()`, en vez de usar un tono puro en la frecuencia central es para simular el modelo de campo difuso. En una sala real, la cola de reverberación de cada banda no es un tono limpio sino la superposición de muchísimas reflexiones aleatorias con energía concentrada en esa banda, que es justamente lo que aporta el ruido filtrado. Además, el uso de un decaimiento exponencial en la ecuación 14 es debido a que el decaimiento físico teórico de las reflexiones en un recinto corresponde a una curva exponencial.

Por otro lado, `filtro_octava` se importa dentro de la función (no al principio del módulo) para evitar una importación circular entre `signal_utils.py` y `filter.py`.

Finalmente, el resultado final se normaliza dividiendo por su valor absoluto máximo y escalando a 0.9, igual que en `cargar_audio()`, dejando el mismo margen de headroom en toda señal que sale del pipeline.

Esta función cuenta con dos tests. El primero simplemente verifica que la duración de la RI generada coincida con la solicitada, en cantidad de muestras. El segundo es el más relevante: genera una RI con un T60 objetivo conocido (2.0 s) en la banda de 1000 Hz, filtra el resultado por esa misma banda, calcula su integral de Schroeder en dB, y mide en qué instante la curva cruza los −60 dB. Ese T60 medido se compara contra el T60 objetivo con una tolerancia del 10%, confirmando que el modelo de síntesis (ruido filtrado + envolvente exponencial) efectivamente produce el tiempo de reverberación esperado y no solo una forma de onda que decae "más o menos" como se espera.

## 3.4.4 Obtención de RI a partir de la grabación de un sweep senoidal

Un servicio vital del proyecto es `obtener_ri_desde_sweep()`, que permite obtener la respuesta al impulso de un recinto a partir de la grabación real de un sine sweep. Recibe la grabación y el filtro inverso del sweep utilizado (los mismos que devuelve `generar_sine_sweep()`), y devuelve la RI estimada, ya recortada y normalizada.

El fundamento es la deconvolución mediante convolución con el filtro inverso, tal como se planteó en la ecuación 5 del marco teórico: al convolucionar la grabación (sweep * h, donde h es la RI del recinto) con el filtro inverso del sweep, el resultado converge a una aproximación de h. La problemática en esta función es determinar cuándo se considera el inicio de la respuesta al impulso. En el caso de considerar el pico como el inicio, se despreciaría completamente toda la respuesta del recinto frente al ataque del impulso. Es por eso que se determinó un criterio de "onset" que determina desde dónde se considera el valor inicial de la respuesta al impulso. Para tener un mejor entendimiento de esta función se enumeran los siguientes pasos de su funcionalidad:

1. Convoluciona la grabacion con filtro_inverso mediante `fftconvolve(..., mode="full")` de scipy.signal, obteniendo la RI cruda ("ri_full"), que incluye tanto la parte previa al sonido directo como toda la cola de reverberación. El "mode="full" es para conservar toda la señal resultante en vez de recortarla prematuramente.
2. Estima el RMS del ruido de fondo usando el último 10% de esa señal, asumiendo que para ese punto la reverberación ya decayó y solo queda ruido.
3. Calcula un umbral 20 dB por encima de ese RMS (llamado margen_db en la función, configurable, 20 dB por defecto).
4. Ubica el pico de la RI mediante `np.argmax` del valor absoluto y retrocede muestra a muestra desde ahí hasta encontrar el primer punto donde la señal cae por debajo del umbral. Ese será el verdadero inicio del sonido directo. Si se buscara el valor que supera los 20 dB desde el inicio, un pico de ruido previo al sonido directo podría detectarse como un falso onset. Partir del pico garantizado (el sonido directo, siempre la muestra de mayor energía) y retroceder evita ese problema.
5. Recorta la RI desde ese valor en adelante y la normaliza a 0.9 de pico para tener un margen.

Las siguientes imágenes ilustran este proceso paso a paso sobre una RI real, medida en una sala con el script "medir_ri.py".

Así se ve, en la Figura 3, la RI recién obtenida de la convolución, sin ningún recorte. Es una señal larga que contiene la respuesta al impulso del recinto (el pico de sonido directo y su cola de reverberación) precedida por una región de ruido de fondo.

![RI medida — convolución completa](m2/imagenes/ri_medida_completa.png)

*Figura 3: RI medida, convolución completa sin recorte.*

La Figura 4 muestra el criterio para determinar el piso de ruido: se toma el último 10% de la convolución completa (la región sombreada), asumiendo que para ese tramo la reverberación ya decayó por completo y solo queda ruido de fondo de la grabación. Con eso se calcula el RMS del ruido, y el umbral de detección se fija 20 dB por encima de ese valor.

![Estimación del piso de ruido en la convolución completa](m2/imagenes/ri_medida_piso_ruido.png)

*Figura 4: Estimación del piso de ruido sobre la convolución completa.*

Con ese umbral ya definido, la línea punteada de la Figura 5 marca el onset: el instante, retrocediendo desde el pico, a partir del cual la señal supera continuamente el umbral. Ahí es donde se recorta la señal. Todo lo anterior al onset se descarta por considerarse piso de ruido.
![RI medida — convolución completa con umbral temporal](m2/imagenes/ri_medida_completa_onset.png)

*Figura 5: RI medida con el umbral temporal de recorte (onset).*

La Figura 6 muestra cómo queda la señal finalmente devuelta por `obtener_ri_desde_sweep()`, recortada desde el onset, conservando una fracción del ataque de la envolvente, para no perder información de la llegada temprana del sonido directo y normalizada a 0.9 de pico, ya lista para pasar al resto del pipeline de análisis.

![RI medida — procesada](m2/imagenes/ri_medida_procesada.png)

*Figura 6: RI medida, ya procesada por `obtener_ri_desde_sweep`.*

Esta función cuenta con un test que valida el caso de uso completo de punta a punta: genera un sweep y su filtro inverso, define una RI conocida (un tono de 1000 Hz con decaimiento exponencial), simula la grabación convolucionando el sweep con esa RI, y aplica `obtener_ri_desde_sweep()` sobre esa grabación simulada. Como el recorte por onset puede introducir un pequeño desfasaje temporal entre la RI original y la recuperada, la comparación no se hace muestra a muestra sino por correlación cruzada normalizada entre ambas señales, calculada con `correlate` de `scipy.signal`, exigiendo que el pico de correlación supere 0.9, es decir, que la forma de onda recuperada sea prácticamente idéntica a la original, sea cual sea el corrimiento temporal que haya introducido la detección del onset.

## 3.4.5 Cambio de escala: La escala logarítmica

Muchos de los gráficos y funciones del proyecto (la curva de Schroeder, la envolvente de una RI, etc) se entienden mejor en escala logarítmica que en amplitud lineal, porque el oído y los parámetros acústicos de la norma trabajan en dB. Esa conversión la hace `a_escala_log()`, calculando el nivel en decibeles según la ecuación 16:

$$L(t) = 20 \log_{10}\!\left(\frac{|h(t)|}{\max(|h|)}\right) \tag{16}$$

De modo que el pico de la señal siempre quede normalizado a 0 dB y el resto de los valores queden expresados en dB relativos a ese pico.

Antes de calcular el logaritmo, la función le aplica un piso a la relación de amplitudes, de forma que ningún valor caiga por debajo del equivalente a −120 dB. Esto es necesario porque una señal real casi siempre tiene tramos de silencio o valores muy cercanos a cero, y el logaritmo de cero es menos infinito. Aplicar el piso antes del logaritmo, en vez de después, evita ese problema de raíz. Se optó por un piso fijo de −120 dB en lugar de usar el porque −120 dB es un valor con sentido físico, aproximado al límite práctico del rango dinámico de una medición acústica real. También se contempla el caso borde de una señal completamente en silencio, con máximo absoluto igual a cero. En vez de dividir por cero, la función devuelve directamente un array del mismo largo lleno de −120 dB, el piso mínimo, que es la lectura correcta para una señal sin ninguna energía.

Esta función tiene tres tests, todos con señales simples y valores conocidos de antemano para poder verificar el cálculo a mano. Uno confirma que el valor máximo de la señal de entrada efectivamente se traduce en 0 dB en la salida. Otro simplemente chequea que el tipo de retorno sea un array de Numpy. El último es el más significativo desde lo acústico toma una señal con un valor que es exactamente la mitad de otro, y verifica que la diferencia entre ambos en la salida sea de −6 dB.

### 3.5 Milestone 3 — Análisis acústico y API REST

## 3.5.1 Suavizado de señales

A la hora de representar visualmente una respuesta al impulso, los gráficos reales contienen fluctuaciones muy rápidas entre muestras que dificultan visualizar la tendencia de decaimiento. Es por eso que resulta conveniente aplicar un método de suavizado que permita reducir estas fluctuaciones. De eso se encarga `suavizar_signal()`, que admite dos modos de suavizado según el parámetro "ventana".

El modo por defecto, "hilbert", calcula la envolvente instantánea de la señal mediante la transformada de Hilbert de `scipy.signal`, según la ecuación 17:

$$A(t) = \left| x(t) + j\hat{x}(t) \right| \tag{17}$$

Donde $\hat{x}(t)$ es la transformada de Hilbert de la señal original. Este modo es el preferido porque no requiere elegir ningún tamaño de ventana arbitrario, la envolvente sale directamente de la señal analítica. 

No obstante también se optó por otro método. Aceptando un entero como tamaño de ventana, se calcula una media móvil sobre la energía de la señal (la señal al cuadrado), según la ecuación 18:

$$y[n] = \frac{1}{M}\sum_{k=0}^{M-1} x^2[n-k] \tag{18}$$

Donde $M$ es el tamaño de la ventana en muestras. Esta alternativa es más simple de entender, pero requiere elegir manualmente el valor de $M$, algo que la envolvente de Hilbert evita. 

No obstante ambos modos son válidos, y el método de la media móvil puede resultar más conveniente si se busca simplificar mucho más un gráfico para facilitar su entendimiento. Si se desea utilizar la media móvil, basta con seleccionar el tamaño de ventana en la entrada de la función.

Finalmente, esta función cuenta con tres tests. Dos validan el modo Hilbert: uno confirma que la envolvente resultante nunca sea negativa (por ser un valor absoluto, tiene que cumplirse siempre), y otro que la señal suavizada conserve la misma longitud que la señal de entrada. El tercero valida el modo de media móvil, comprobando también que preserve la longitud original.

## 3.5.2 Integral de Schroeder

Tal como se planteó en la ecuación 9 del marco teórico, la curva de decaimiento energético se obtiene sumando, para cada instante $n$, toda la energía restante de la señal desde $n$ hasta el final. Esa es la responsabilidad de `integral_schroeder()`, recibir una RI (idealmente ya filtrada por banda) y devolver la curva de decaimiento en dB, normalizada a 0 dB en su primer valor.

La implementación evita calcular esa suma de forma literal y en cambio aprovecha `np.cumsum` sobre la señal de energía invertida. Al sumar acumulativamente de atrás para adelante sobre la energía invertida da, al revertir el resultado, exactamente la misma suma que pide la ecuación 9, pero con mucho menos procesamiento y menor tiempo de respuesta. Una vez obtenida esa integral, se la convierte a dB normalizando por su primer valor (que es la energía total de la señal), según la ecuación 19:

$$L[n] = 10 \log_{10}\!\left(\frac{E[n]}{E[0]}\right) \tag{19}$$

De modo que la curva siempre arranca en 0 dB, es decir, con toda la energía todavía por delante, y decae a medida que $n$ avanza y hay menos energía remanente. Antes de aplicar el logaritmo se acota el cociente con un piso "EPS" (el épsilon de máquina, es decir, el número más pequeño que puede soportar) para evitar el mismo problema de log10(0) que ya se resolvió en `a_escala_log()`, solo que en este caso no importa que el piso sea demasiado bajo. Como caso borde, si la energía total de la señal es cero (una RI de puro silencio), la función devuelve directamente un array de "-inf" del mismo largo, en vez de dividir por cero.

Esta función cuenta con cuatro tests. Los dos primeros son de forma: que la curva devuelta tenga la misma longitud que la RI de entrada, y que su primer valor sea efectivamente 0 dB. El tercero verifica que la curva sea monótonamente decreciente en toda su extensión, una propiedad que se cumple por construcción matemática (nunca se le puede sumar energía negativa a la integral) y que sirve como chequeo de que la implementación no tenga errores de signo o de indexado. El cuarto es el más relevante desde lo acústico. Se sintetiza una RI con un T60 conocido de antemano, calcula su integral de Schroeder, ajusta una recta por mínimos cuadrados en el rango típico de T30 (−5 a −35 dB), y verifica que el T60 estimado a partir de esa pendiente esté dentro de un 30% del valor real usado para sintetizar la señal, confirmando que la curva no solo decrece, sino que lo hace a la velocidad correcta.

## 3.5.2 Integral de Schroeder

En `regresion_lineal()` se implementa el método de cuadrados mínimos planteado en el marco teórico (ecuaciones 10 a 13). Recibe dos arrays, típicamente el tiempo y la curva de Schroeder en dB dentro del rango de interés, y devuelve la pendiente $m$, la ordenada al origen $b$ y el coeficiente de determinación $R^2$, calculados exactamente según esas mismas fórmulas.

La implementación contempla dos casos borde que las fórmulas puras no resuelven por sí solas. El primero es cuando el denominador de la ecuación 11 da cero, algo que ocurre si todos los valores de $x$ son iguales entre sí (una recta horizontal). En ese caso no existe una pendiente bien definida, así que la función devuelve pendiente 0, la ordenada como el promedio de $y$, y $R^2 = 0$. El segundo es cuando la varianza total de $y$ (el denominador de la ecuación 13) es cero, es decir, todos los puntos $y$ son idénticos; ahí cualquier recta horizontal ajusta perfectamente, así que se devuelve $R^2 = 1$ en vez de una división por cero.

Vale aclarar que esta función solo calcula el ajuste, no decide si ese ajuste es aceptable. Esa validación se deriva a las siguientes funciones del pipeline.

Esta función tiene tres tests. El primero verifica el caso más simple: una recta perfectamente conocida ($y = 2x + 1$, sin ruido), confirmando que la pendiente y la ordenada recuperadas coincidan con los valores exactos usados para generarla. El segundo confirma que, para datos perfectamente lineales, el $R^2$ calculado sea exactamente 1.0, el máximo posible. El tercero prueba un caso más realista: una recta conocida ($y = 3x + 5$) a la que se le agrega ruido gaussiano, y verifica que la pendiente y la ordenada estimadas sigan estando razonablemente cerca de los valores reales pese al ruido, validando que el método sea robusto a pequeñas perturbaciones, no solo exacto en el caso ideal sin ruido.

## 3.5.2 Método Lundeby

El método Lundeby es un método para truncar el piso de ruido de la curva de Schroeder. El problema de la integral de Schroeder es que no sabe dónde empieza el ruido, por lo que si se le da una RI de mucha duración, considerará al piso de ruido en la integral y eso resultará posteriormente en un peor ajuste lineal. Para solventar esta carencia, el método Lundeby propone separar al tiempo en bloques de 10 ms (ventanas), hacer una estimación del nivel del piso de ruido utilizando el último 10% de la señal, buscar el primer bloque donde la energía cae dentro de un margen de 10 dB cercanos al piso de ruido, y realizar un ajuste lineal entre el inicio de la curva y ese bloque. Luego, se busca la intersección entre esa recta ajustada y el piso de ruido calculado, y promedia el nivel de la señal luego de esa intersección, para obtener un nuevo nivel de piso de ruido y así repetir todo el proceso nuevamente.  

La función `metodo_lundeby()` implementa este algoritmo llamando directamente a `regresion_lineal()`,definiendo una función auxiliar interna llamada `_primer_cruce_sostenido()`.En vez de tomar como válido el primer bloque que cae por debajo del umbral, esa función auxiliar exige varios bloques consecutivos por debajo del margen de 10 dB, y descarta cualquier candidato dentro de los primeros bloques de la señal, precisamente para no confundir un nulo modal aislado (algo típico en bandas graves como 125 Hz, donde hay poca densidad de modos) con el verdadero comienzo del piso de ruido. A esto se suma otra salvaguarda dentro del bucle principal: cada vez que se reestima el nivel de ruido tras un nuevo truncamiento, ese nuevo valor solo se acepta si no supera en más de 3 dB a la estimación de referencia inicial, evitando que el algoritmo entre en una realimentación positiva donde, iteración tras iteración, el truncamiento se corre cada vez más temprano devorando cola reverberante real en vez de ruido. El proceso se repite hasta que el punto de truncamiento deja de moverse de una iteración a la siguiente, con un tope de 15 iteraciones para garantizar que la función siempre termine.

Esta función cuenta con cuatro tests. Uno verifica simplemente los tipos de retorno y que el índice de truncamiento devuelto esté dentro del rango válido de la señal. Otro confirma que, al agregarle ruido de fondo real a una RI sintetizada, el truncamiento efectivamente ocurra antes del final de la señal (y no al final, como pasaría si no detectara el ruido). Un tercero compara dos versiones de la misma RI, una limpia y otra con ruido agregado, y verifica que la versión ruidosa trunque en un punto más temprano que la limpia, tal como se espera si el algoritmo está reaccionando al ruido y no ignorándolo. El último valida la precisión de la estimación en sí: agrega ruido de fondo con un nivel conocido de antemano y verifica que el nivel de ruido estimado por la función esté dentro de ±6 dB del valor real.

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