# Validación Milestone 1 — Generación de Señales

Este documento presenta la validación visual de las tres funciones implementadas en M1:
`generar_ruido_rosa`, `generar_sine_sweep` y la verificación de que la convolución
sweep × filtro inverso converge a un impulso.

Los gráficos de PSD y convolución fueron generados con el script `generar_graficos.py`.
Los espectrogramas fueron generados con **Audacity** exportando las señales a WAV.

---

## 1. Ruido rosa

El ruido rosa (ruido **1/f**) se define por tener una densidad espectral de potencia
inversamente proporcional a la frecuencia:

$$S(f) = \frac{k}{f}$$

En escala logarítmica esto corresponde a una caída de exactamente **−3 dB por octava**:

$$\Delta L = 10 \log_{10}\!\left(\frac{1}{2}\right) \approx -3{,}01 \text{ dB}$$

### 1.1 PSD con referencia teórica (Welch)

![PSD ruido rosa](imagenes/ruido_rosa_espectro.png)

La pendiente medida con el método de Welch sobre 10 segundos de señal es **−3.01 dB/oct**,
prácticamente coincidente con el valor teórico (línea roja discontinua).
El test automatizado verifica que la pendiente esté dentro del rango −4 a −2 dB/oct,
criterio que esta implementación supera con amplitud.

### 1.2 Análisis espectral en Audacity

![Espectro ruido rosa Audacity](<imagenes/Espectro ruido rosa con caida 3dB por octava.png>)

El análisis de frecuencia en Audacity confirma visualmente la caída progresiva de nivel
a medida que aumenta la frecuencia. La envolvente espectral sigue una pendiente
consistente con −3 dB/oct en toda la banda audible, coherente con el comportamiento
teórico del ruido 1/f.

### 1.3 Espectrograma en Audacity

![Espectrograma ruido rosa](<imagenes/Pink noise espectrograma.png>)

El espectrograma muestra la distribución de energía en tiempo y frecuencia.
La densidad de color es uniforme en toda la banda y a lo largo del tiempo, lo cual
es la firma característica del ruido rosa: igual energía por octava, sin preferencia
temporal ni espectral. Esto contrasta claramente con el ruido blanco (que sería
más brillante en frecuencias altas) y confirma el comportamiento 1/f de la señal generada.

---

## 2. Sine sweep logarítmico

El sine sweep logarítmico se define por una frecuencia instantánea que crece
exponencialmente con el tiempo:

$$f(t) = f_1 \cdot e^{\,t \ln(f_2/f_1)/T}$$

La elección logarítmica garantiza igual energía por octava, haciéndolo compatible con
los filtros de banda IEC 61260 que se usarán en M2.

### 2.1 Forma de onda

![Forma de onda del sweep](imagenes/sweep_forma_onda.png)

La forma de onda muestra el comportamiento característico del sweep logarítmico:
la frecuencia instantánea crece lentamente al principio (bajas frecuencias, ciclos
visibles más anchos a la izquierda) y se acelera hacia el final (altas frecuencias,
ciclos tan comprimidos que la señal parece sólida a la derecha).

### 2.2 Espectrograma en Audacity

![Espectrograma del sweep](<imagenes/Sine sweep espectrograma.png>)

El espectrograma confirma que la frecuencia instantánea crece de forma
**monótonamente creciente** de 20 Hz a 20 kHz a lo largo de los 5 segundos.
La curva brillante describe una trayectoria exponencial (recta en escala log-lineal),
característica definitoria del sweep logarítmico. No se observan discontinuidades
ni saltos de frecuencia, lo que valida la correcta implementación de la función.

---

## 3. Convolución sweep × filtro inverso → impulso

El fundamento de la técnica de Farina (2000) es que la convolución del sweep con su
filtro inverso debe aproximarse a una delta de Dirac:

$$x(t) * x_{\text{inv}}(t) \approx \delta(t)$$

El filtro inverso compensa la distribución no uniforme de energía del sweep logarítmico
invirtiendo temporalmente la señal y aplicando una envolvente de corrección:

$$x_{\text{inv}}(t) = \frac{x(T - t)}{A(t)}, \quad A(t) = e^{-t \ln(f_2/f_1)/T}$$

![Convolución sweep × filtro inverso — vista completa](imagenes/convolucion_completa.png)

Toda la energía de la señal resultante está concentrada en un único instante (t = 5 s),
con el resto de la señal prácticamente en cero.

![Convolución sweep × filtro inverso — zoom ±5 ms](imagenes/convolucion_zoom.png)

El resultado es un pulso estrecho con lóbulos laterales mínimos — la aproximación
práctica al impulso ideal δ(t).

La relación señal a ruido pico/piso medida es de **≈ 101.7 dB**, muy por encima del
umbral mínimo de 40 dB que exige el test automatizado. Esto garantiza que la
deconvolución en M2 producirá una respuesta al impulso con alta resolución y bajo
nivel de artefactos.

---

## Resumen de validación

| Señal | Criterio | Resultado | Estado |
|---|---|---|---|
| Ruido rosa | Pendiente −3 ± 1 dB/oct | −3.01 dB/oct | ✓ |
| Ruido rosa | Distribución uniforme en el tiempo | Confirmado en espectrograma | ✓ |
| Sine sweep | Barrido monótono 20 Hz → 20 kHz | Confirmado en espectrograma | ✓ |
| Convolución sweep × inverso | SNR pico/piso ≥ 40 dB | ≈ 101.7 dB | ✓ |

---

**Referencia:** Farina, A. (2000). *Simultaneous measurement of impulse response and
distortion with a swept-sine technique.* 108th AES Convention.
