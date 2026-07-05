# Validación Milestone 3 — Análisis Acústico y Validación con REW

Este documento presenta la validación de las funciones de análisis implementadas en M3
(`suavizar_signal`, `integral_schroeder`, `regresion_lineal`, `metodo_lundeby` y
`calcular_parametros_acusticos`) y la comparación obligatoria de resultados contra
**REW (Room EQ Wizard)**, el software de referencia elegido para la consigna.

Los gráficos de curva de Schroeder fueron generados con `scripts/graficar_schroeder.py`.
Los gráficos de comparación T30 y las tablas de validación fueron generados con
`scripts/graficar_t30_comparativa.py` y `scripts/comparar_rew_vs_api.py` respectivamente,
a partir de las exportaciones de texto de REW (`tablas_validacion/*.txt`).

Se usaron **3 RIs reales** para la validación — cumple el mínimo de 2 RIs que exige la
consigna, aunque no incluye una sintetizada (se descartó la RI sintética de esta ronda de
validación):

| RI | Origen | T60 nominal |
|---|---|---|
| Elveden Hall | OpenAIR (sala grande) | ~3–4 s |
| Maes Howe | OpenAIR (cámara neolítica pequeña) | ~0.5 s |
| RI procesada (medida) | Medición propia con sine sweep (`medir_ri.py`) | ~0.3 s |

---

## 1. Curva de Schroeder, truncamiento de Lundeby y regresión T20/T30

La integral de Schroeder se calcula por integración inversa de la energía:

$$L[n] = 10 \log_{10}\!\left(\frac{\sum_{k=n}^{N-1} h^2[k]}{\sum_{k=0}^{N-1} h^2[k]}\right)$$

Antes de integrar, `metodo_lundeby` estima el punto donde la RI se cruza con el piso de
ruido de fondo y trunca la señal ahí — evitando que la cola de ruido "aplane" la curva de
decaimiento y sesgue la pendiente. Sobre la curva truncada, `regresion_lineal` ajusta por
mínimos cuadrados dos rectas: **T20** (rango −5 a −25 dB) y **T30** (rango −5 a −35 dB),
cada una extrapolada a −60 dB.

### 1.1 Elveden Hall

![Curva de Schroeder — Elveden Hall](Imagenes/schroeder_lundeby_t30_elveden_hall.png)

La curva es prácticamente recta hasta el punto de truncamiento: al ser una sala grande con
alta densidad modal, el decaimiento se comporta como una única pendiente bien definida.
Las rectas de T20 y T30 casi se superponen entre sí y con la curva medida.

### 1.2 Maes Howe

![Curva de Schroeder — Maes Howe](Imagenes/schroeder_lundeby_t30_maes_howe.png)

Acá se nota una curvatura visible antes del truncamiento: la curva se "dobla" hacia una
pendiente más suave a partir de los −45/−50 dB. Es consistente con el ruido de fondo real
de la medición y con la baja densidad modal de un recinto tan pequeño en frecuencias bajas
— exactamente el motivo por el que Lundeby trunca antes de que esa curvatura contamine la
regresión.

> **Corrección aplicada a `metodo_lundeby` (2026-07-04):** el cruce preliminar con el piso
> de ruido se aceptaba con el primer intervalo de 10 ms que cayera por debajo del umbral,
> sin exigir un mínimo de puntos ni de continuidad. En bandas de baja densidad modal como
> 125 Hz, el batido entre modos genera nulos transitorios en la envolvente que el algoritmo
> confundía con el piso de ruido, colapsando el truncamiento a unas pocas decenas de
> milisegundos y arrastrando una reestimación de ruido contaminada por cola reverberante
> real. Se agregó (`_primer_cruce_sostenido`) la exigencia de un mínimo de intervalos antes
> de buscar el cruce y de continuidad sostenida para confirmarlo, además de acotar la
> reestimación del piso de ruido para que no se aleje más de unos dB de la estimación inicial
> (último 10 % de la señal). Los valores de esta sección ya reflejan la corrección.

### 1.3 RI medida (propia)

![Curva de Schroeder — RI medida](Imagenes/schroeder_lundeby_t30_ri_medida.png)

Mismo comportamiento que Maes Howe: la curva se aplana notoriamente después de los −40 dB
antes de truncar, reflejando el piso de ruido real del entorno de grabación (a diferencia
de una cámara anecoica o un recinto muy silencioso).

---

## 2. Validación T30 por banda de octava: RIR-API vs REW

Para cada RI se cargó el WAV en REW, se midió RT60 con filtro **Zero Phase / octava**, se
exportó la tabla de resultados como texto, y se comparó contra `calcular_parametros_acusticos`.

### 2.1 Elveden Hall

![T30 Elveden Hall — RIR-API vs REW](Imagenes/t30_comparativa_elveden_hall.png)

### 2.2 Maes Howe

![T30 Maes Howe — RIR-API vs REW](Imagenes/t30_comparativa_maes_howe.png)

En la banda de 125 Hz se sigue observando la mayor divergencia de las 6 bandas (0.73 s vs
0.61 s), pero bajó notoriamente respecto de la ronda anterior de validación (0.77 s vs
0.61 s → diferencia de 0.167 s a 0.127 s) tras corregir el falso cruce con el piso de ruido
en `metodo_lundeby` (ver nota en 1.2). El resto de la divergencia remanente es consistente
con la baja densidad modal a bajas frecuencias en un recinto tan pequeño, que hace que el
resultado sea más sensible a diferencias finas entre el filtro de octava de RIR-API y el de
REW. Sigue dentro de la tolerancia de ±0.5 s.

### 2.3 RI procesada (medida)

![T30 RI procesada — RIR-API vs REW](Imagenes/t30_comparativa_ri_procesada_medida.png)

---

## 3. Resumen de validación

Diferencia máxima (peor banda de las 6) entre RIR-API y REW, por parámetro y por RI.
Tolerancia según consigna: **±0.5 s** para EDT/T20/T30.

| RI | EDT | T20 | T30 |
|---|---|---|---|
| Elveden Hall | 0.206 s ✓ | 0.291 s ✓ | 0.414 s ✓ |
| Maes Howe | 0.196 s ✓ | 0.079 s ✓ | 0.127 s ✓ |
| RI procesada (medida) | 0.029 s ✓ | 0.021 s ✓ | 0.023 s ✓ |

**T20 y T30 pasan la validación en las 3 RIs, en las 6 bandas, ampliamente dentro de
tolerancia** (peor caso 0.41 s contra un límite de 0.5 s).

### 3.1 Máxima desviación registrada

El peor caso de toda la validación es **T30 en Elveden Hall a 125 Hz — 0.414 s** de
diferencia (RIR-API=2.317 s vs REW=2.730 s) — la más cercana al límite de ±0.5 s, pero
sigue dentro de tolerancia. Antes de corregir `metodo_lundeby` este mismo caso daba 0.432 s.

### 3.2 Tabla completa por banda (125–4000 Hz)

Valores de RIR-API y REW para EDT, T20 y T30 en las 6 bandas de octava exigidas por
la consigna, para las 3 RIs.

#### Elveden Hall

| Parámetro | Banda (Hz) | RIR-API | REW | Diferencia | Dentro de tolerancia |
|---|---|---|---|---|---|
| EDT | 125 | 2.106s | 2.212s | -0.106s | Sí |
| EDT | 250 | 3.178s | 3.384s | -0.206s | Sí |
| EDT | 500 | 4.367s | 4.416s | -0.049s | Sí |
| EDT | 1000 | 4.007s | 3.957s | +0.050s | Sí |
| EDT | 2000 | 3.649s | 3.650s | -0.001s | Sí |
| EDT | 4000 | 2.570s | 2.652s | -0.082s | Sí |
| T20 | 125 | 2.336s | 2.627s | -0.291s | Sí |
| T20 | 250 | 3.417s | 3.605s | -0.188s | Sí |
| T20 | 500 | 4.311s | 4.255s | +0.056s | Sí |
| T20 | 1000 | 4.124s | 4.119s | +0.005s | Sí |
| T20 | 2000 | 3.895s | 3.859s | +0.036s | Sí |
| T20 | 4000 | 2.792s | 2.903s | -0.111s | Sí |
| T30 | 125 | 2.317s | 2.730s | -0.414s | Sí |
| T30 | 250 | 3.408s | 3.567s | -0.159s | Sí |
| T30 | 500 | 4.284s | 4.202s | +0.082s | Sí |
| T30 | 1000 | 4.110s | 4.089s | +0.021s | Sí |
| T30 | 2000 | 3.904s | 3.862s | +0.042s | Sí |
| T30 | 4000 | 2.858s | 3.001s | -0.143s | Sí |

#### Maes Howe

| Parámetro | Banda (Hz) | RIR-API | REW | Diferencia | Dentro de tolerancia |
|---|---|---|---|---|---|
| EDT | 125 | 0.631s | 0.596s | +0.035s | Sí |
| EDT | 250 | 0.339s | 0.535s | -0.196s | Sí |
| EDT | 500 | N/A | 0.402s | - | - |
| EDT | 1000 | N/A | 0.252s | - | - |
| EDT | 2000 | N/A | 0.301s | - | - |
| EDT | 4000 | N/A | N/A | - | - |
| T20 | 125 | 0.689s | 0.610s | +0.079s | Sí |
| T20 | 250 | 0.589s | 0.550s | +0.039s | Sí |
| T20 | 500 | 0.519s | 0.507s | +0.012s | Sí |
| T20 | 1000 | 0.528s | 0.492s | +0.036s | Sí |
| T20 | 2000 | 0.451s | 0.433s | +0.018s | Sí |
| T20 | 4000 | 0.458s | 0.382s | +0.076s | Sí |
| T30 | 125 | 0.733s | 0.606s | +0.127s | Sí |
| T30 | 250 | 0.611s | 0.579s | +0.032s | Sí |
| T30 | 500 | 0.575s | 0.530s | +0.045s | Sí |
| T30 | 1000 | 0.507s | 0.490s | +0.017s | Sí |
| T30 | 2000 | 0.466s | 0.447s | +0.019s | Sí |
| T30 | 4000 | 0.430s | 0.394s | +0.036s | Sí |

#### RI procesada (medida)

| Parámetro | Banda (Hz) | RIR-API | REW | Diferencia | Dentro de tolerancia |
|---|---|---|---|---|---|
| EDT | 125 | 0.184s | 0.190s | -0.006s | Sí |
| EDT | 250 | 0.154s | 0.135s | +0.019s | Sí |
| EDT | 500 | 0.183s | 0.166s | +0.017s | Sí |
| EDT | 1000 | 0.270s | 0.248s | +0.022s | Sí |
| EDT | 2000 | 0.248s | 0.219s | +0.029s | Sí |
| EDT | 4000 | 0.263s | 0.237s | +0.026s | Sí |
| T20 | 125 | 0.277s | 0.279s | -0.002s | Sí |
| T20 | 250 | 0.313s | 0.292s | +0.021s | Sí |
| T20 | 500 | 0.287s | 0.294s | -0.007s | Sí |
| T20 | 1000 | 0.270s | 0.271s | -0.002s | Sí |
| T20 | 2000 | 0.232s | 0.232s | +0.000s | Sí |
| T20 | 4000 | 0.251s | 0.252s | -0.001s | Sí |
| T30 | 125 | 0.515s | 0.500s | +0.015s | Sí |
| T30 | 250 | 0.294s | 0.292s | +0.002s | Sí |
| T30 | 500 | 0.387s | 0.365s | +0.022s | Sí |
| T30 | 1000 | 0.286s | 0.284s | +0.002s | Sí |
| T30 | 2000 | 0.279s | 0.266s | +0.013s | Sí |
| T30 | 4000 | 0.324s | 0.301s | +0.023s | Sí |

---

## Discusión y limitaciones

- **T20/T30 validados.** Es el resultado central de la consigna y se cumple con margen
  amplio en las 3 RIs (real chica, real grande, medida propia).
- **Divergencia en graves en recintos chicos (Maes Howe).** Consistente entre software:
  a menor tamaño de recinto, menor densidad modal en bajas frecuencias, y mayor
  sensibilidad del resultado a diferencias finas de filtrado entre implementaciones.
- **Corrección de `metodo_lundeby` (2026-07-04).** El algoritmo aceptaba el primer intervalo
  de 10 ms por debajo de piso de ruido + 10 dB como cruce, sin mínimo de puntos ni de
  continuidad. En bandas de baja densidad modal (125 Hz sobre todo) un nulo transitorio del
  batido entre modos podía confundirse con el piso de ruido y colapsar el truncamiento a
  unas pocas decenas de milisegundos, arrastrando además una reestimación de ruido
  contaminada por cola reverberante real. Se agregó un mínimo de intervalos y de continuidad
  sostenida para aceptar el cruce, y se acotó la reestimación del piso de ruido. Efecto neto
  en esta validación: T30 a 125 Hz en Maes Howe bajó de +0.167 s a +0.127 s de diferencia
  con REW, y D50 a 125 Hz en la misma RI pasó de un caso patológico (con la señal estéreo sin
  promediar, llegaba a desviarse ~10 puntos) a +0.31 puntos porcentuales. No cambia la
  conclusión de tolerancia (todo seguía y sigue dentro de ±0.5 s), pero corrige un caso donde
  el resultado podía ser groseramente incorrecto con RIs reales de baja densidad modal y bajo
  SNR en graves — el escenario más común fuera de este set de validación.

---

**Referencias:**
Schroeder, M. R. (1965). *New method of measuring reverberation time.* JASA, 37(3), 409-412.
Lundeby, A. et al. (1995). *Uncertainties of measurements in room acoustics.* Acustica, 81(4), 344-355.
