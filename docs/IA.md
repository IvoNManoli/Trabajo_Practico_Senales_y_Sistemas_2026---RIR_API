# AI_LOG.md — Registro de uso de IA

## Información del Proyecto

| Parámetro | Detalle |
| :--- | :--- |
| **Materia** | Señales y Sistemas |
| **Universidad** | UNTREF |
| **Proyecto** | RIR-API — API REST para cálculo de parámetros acústicos ISO 3382 |
| **Integrantes** | Ivo Manoli, Agustín Birarelli, Gaspar Dallinge |

---

## M1 — Generación de Señales

### Sesión 1 — 01/06/2026 (Claude Web)

| Campo | Detalle |
| :--- | :--- |
| **Herramienta** | Claude (claude.ai) |
| **Prompt resumido** | Diagnóstico del estado de M1, corrección de firma de `reproducir_y_grabar` e implementación del test de convolución sweep × filtro inverso |
| **Resultado** | Se identificaron 4 pendientes: firma incorrecta de `reproducir_y_grabar`, falta del test de convolución, falta del tag `v0.1.0` y `ci.yml` apuntando a `src/` en lugar de `app/`. Se corrigió la firma (`num_canales` → `duracion_grabacion`) y se implementó `test_convolucion_genera_impulso` con resultado 7/7 tests en verde |
| **Evaluación** | El diagnóstico fue preciso. El test de convolución no es solo una validación técnica: entender que sweep × filtro_inverso ≈ δ(t) es el principio fundamental detrás de la medición de RI que se usará en M2 |

---

### Sesión 2 — 02/06/2026 (Claude Code en VS Code)

| Campo | Detalle |
| :--- | :--- |
| **Herramienta** | Claude Code (claude-sonnet-4-6, extensión VS Code) |
| **Prompt resumido** | Cierre de M1: test de `reproducir_y_grabar`, fix de CI, documentación de validación visual con gráficos |
| **Resultado** | (1) Se agregó `TestReproducirYGrabar` con 4 tests usando `unittest.mock` (acepta 1D y 2D, duración ±1%, RuntimeError sin device). (2) Se corrigió `ci.yml`: `ruff check src/` → `ruff check app/`. (3) Se creó `generar_graficos.py` que produce PSD del ruido rosa (Welch), forma de onda del sweep y gráfico de convolución. (4) Se creó `validacion_m1.md` documentando cada gráfico con su fundamento teórico, incorporando también espectrogramas generados con Audacity. (5) Se subieron las consignas M0–M3 a `feature/documentacion`. 11/11 tests en verde |
| **Evaluación** | Claude Code en VS Code permite trabajar directamente sobre el repositorio sin necesidad de exportar contexto manualmente. El uso de `unittest.mock` para simular el dispositivo de audio fue clave para que los tests de `reproducir_y_grabar` corran en CI sin hardware real. Los espectrogramas de Audacity complementan bien los gráficos programáticos |

---

---

## M2 — Procesamiento de la Respuesta al Impulso

### Sesión 1 — 03/06/2026 (Claude Code en VS Code)

**Herramienta:** Claude Code (claude-sonnet-4-6, extensión VS Code)

---

**1. Lectura de contexto**

- *Prompt:* Leer los archivos de consigna (m0 a m3), los PDFs adjuntos y el CLAUDE.md antes de empezar M2.
- *Respuesta:* Claude leyó los 4 archivos de consigna, los 4 PDFs de la cátedra (presentación general del TP, M0, M1 y marco conceptual) y el CLAUDE.md. Devolvió un resumen del estado del proyecto: M1 completo con tag `v0.1.0`, M2 vence 16/06 con 5 funciones pendientes en stubs, y los tests requeridos según consigna.

---

**2. Implementar `cargar_audio`**

- *Prompt:* Crear `cargar_audio` en `signal_utils.py`.
- *Respuesta:* Se implementó con `soundfile.read(..., dtype='float64', always_2d=False)`, `FileNotFoundError` si el archivo no existe y `ValueError` envolviendo cualquier error de soundfile. La firma se actualizó de `str` a `str | Path`.

---

**3. Implementar `sintetizar_ri`**

- *Prompt:* Crear `sintetizar_ri`.
- *Respuesta:* Para cada banda: genera ruido blanco, aplica `filtro_octava`, multiplica por la envolvente `exp(-α·t)` con `α = 6.908/T60`. Suma las bandas y normaliza al 90%. El import de `filtro_octava` se hace dentro de la función para evitar importación circular al momento de cargar el módulo.

---

**4. Implementar `filtro_octava`**

- *Prompt:* Crear `filtro_octava`.
- *Respuesta:* Frecuencias de corte IEC 61260: `f_inf = fc/√2`, `f_sup = fc·√2`. Diseño con `scipy.signal.butter` (Butterworth) + `filtfilt` (fase cero, necesario para EDT y T60). Se agrega un clamp `min(f_sup/nyq, 0.9999)` para bandas altas como 16 kHz a 44.1 kHz donde `f_sup` supera Nyquist.

---

**5. Implementar `a_escala_log`**

- *Prompt:* Crear `a_escala_log`.
- *Respuesta:* `20·log10(|h|/max|h|)`. El piso de −120 dB se aplica antes del log reemplazando valores bajos por `10^(-120/20) = 1e-6` para evitar `log(0)`. Si la señal es todo ceros devuelve un array de −120 dB directamente.

---

**6. Implementar `obtener_ri_desde_sweep`**

- *Prompt:* Crear `obtener_ri_desde_sweep`.
- *Respuesta:* `fftconvolve(grabacion, filtro_inverso, mode='full')`, recorte desde `argmax(|ri_full|)` (sonido directo), normalización al 90%. Se agregó el import de `fftconvolve` al inicio del módulo.

---

**7. Tests de `cargar_audio`**

- *Prompt:* Crear `test_cargar_audio_wav`, `test_cargar_audio_formato_invalido` y `test_cargar_audio_normalizacion`, conservando los tests ya existentes.
- *Respuesta:* Los tres tests usan archivos temporales con `tempfile.NamedTemporaryFile` + `soundfile.write`. `test_cargar_audio_wav` escribe un WAV float32 y verifica shape, fs y valores con `atol=1e-5`. `test_cargar_audio_formato_invalido` escribe bytes de texto inválidos y verifica que se lanza `ValueError`. `test_cargar_audio_normalizacion` usa valores extremos `±1.0` y verifica que todos los valores cargados estén en `[-1, 1]`. Se usó `try/finally` para garantizar que el archivo temporal se elimina aunque el assert falle.

---

**8. Test `test_a_escala_log_relacion`**

- *Prompt:* Agregar el test que verifica que amplitud mitad da −6 dB.
- *Respuesta:* `x = [1.0, 0.5]`, verifica `|db[1] - (-6.0206)| < 0.01`. El valor exacto es `20·log10(0.5) = −6.0206 dB`.

---

**9. Commit tests `cargar_audio` + `a_escala_log`**

- *Prompt:* Hacer commit de los tests creados hasta el momento.
- *Respuesta:* Se verificó el diff con `git diff --cached`, todo correcto. Commit: `test: tests de cargar_audio y a_escala_log (M2)`.

---

**10. Tests de `sintetizar_ri`**

- *Prompt:* Crear `test_sintetizar_ri_duracion` y `test_sintetizar_ri_decaimiento`.
- *Respuesta:* `test_sintetizar_ri_duracion` verifica que `len(ri) == int(duracion * fs)`. `test_sintetizar_ri_decaimiento` usa `np.random.seed(42)` para reproducibilidad, sintetiza con T60=2.0 s y duracion=3.0 s (1.5×T60 para asegurar decaimiento suficiente), filtra en 1000 Hz con `filtro_octava`, calcula la integral de Schroeder backward (`np.cumsum(energia[::-1])[::-1]`), busca el cruce de −60 dB y verifica que el T60 medido esté dentro de ±10% del objetivo.

---

**11. Commit tests `sintetizar_ri`**

- *Prompt:* Hacer commit.
- *Respuesta:* Commit: `test: tests de sintetizar_ri (M2)`.

---

**12. Tests de `filtro_octava`**

- *Prompt:* Crear `test_filtro_octava_frecuencia_central`, `test_filtro_octava_atenuacion` y `test_filtro_octava_respuesta_frecuencia`.
- *Respuesta:* `test_filtro_octava_frecuencia_central` inyecta un seno en fc=1000 Hz por 1 s, excluye el 10% de cada borde para evitar transitorios, y verifica que la ganancia RMS sea `< ±1 dB`. `test_filtro_octava_atenuacion` repite para fc/2 y 2·fc y verifica atenuación `> 20 dB`. `test_filtro_octava_respuesta_frecuencia` llama a `butter` + `freqz` directamente para verificar 0 dB en fc y −3 dB en f_inf/f_sup (el diseño del filtro, no la salida de filtfilt). Hubo que agregar `# type: ignore[misc]` por falsos positivos de Pyright con las sobrecargas de `butter`.

---

**13. Test `test_obtener_ri_pico`**

- *Prompt:* Crear el test de deconvolución verificando correlación cruzada > 0.9.
- *Respuesta:* Genera sweep + filtro_inverso (fs=8000 para velocidad), crea RI conocida como `sin(2π·1000·t)·exp(-5t)`, simula la grabación con `fftconvolve(sweep, ri_orig)`, aplica `obtener_ri_desde_sweep` y verifica correlación cruzada con mejor desfase usando `scipy.signal.correlate(a, b, mode='full')`.

---

**14. Ejecución de pytest — primera corrida**

- *Prompt:* Ejecutar pytest para ver si funcionan todos los tests.
- *Respuesta:* 11/14 passed, 2 failed. **Fallo 1** — `test_cargar_audio_wav`: `soundfile` escribe PCM16 por defecto; la cuantización a 16 bits produce diferencias de hasta `2.4e-5`, mayor que `atol=1e-5`. Solución: agregar `subtype='FLOAT'` al `sf.write`. **Fallo 2** — `test_obtener_ri_pico` con RI `exp(-5t)` daba correlación 0.19 porque el sweep cubre solo 50–3000 Hz y no recupera la energía fuera de esa banda. Se cambió a `sin(2π·1000·t)·exp(-5t)`, pero la correlación fue −0.0007: `sin` empieza en 0 y tiene su máximo en la muestra 2, por lo que `obtener_ri_desde_sweep` recorta ahí y el vector recuperado queda 90° desfasado respecto al original; comparar muestra a muestra da correlación nula. Solución: reemplazar el producto punto por `np.max(np.abs(correlate(a, b, mode='full')))`, que busca el mejor desfase temporal.

---

**15. Test skipped**

- *Prompt:* ¿Por qué hay un test skipped?
- *Respuesta:* Era `test_cargar_audio_retorna_tupla`, un placeholder original con `pytest.skip`. Quedó obsoleto al crear `test_cargar_audio_wav`. Se eliminó.

---

**Resultado final:** 13/13 tests pasan en 0.98 s.

**Evaluación:** Los dos fallos de tests fueron los momentos más valiosos de la sesión. El problema de PCM16 vs FLOAT es un detalle práctico habitual en trabajo con audio. El problema de alineación en `test_obtener_ri_pico` es conceptualmente relevante: `obtener_ri_desde_sweep` recorta desde el pico del sonido directo, que no necesariamente es la muestra 0 de la RI. La solución con correlación cruzada es más robusta y refleja mejor cómo se comparan señales en acústica.

---

---

### Sesión 2 — 15/06/2026 (Claude Code en VS Code)

**Herramienta:** Claude Code (claude-sonnet-4-6, extensión VS Code)

---

**1. Diagnóstico del estado de M2**

- *Prompt:* Revisar el PDF de la clase y `m2_consigna.md`, y evaluar si falta algo para la entrega.
- *Respuesta:* Las 5 funciones y los 13 tests están completos y en verde. Se identificaron 3 pendientes: (1) tag `v0.2.0` no creado (solo existe `v0.1.0`), (2) carpeta `docs/m2/` sin gráficas de validación manual, (3) `pytest-cov` no está en las dependencias de dev por lo que no se puede medir cobertura.

---

**2. Revisión de las gráficas existentes**

- *Prompt:* Revisar `docs/m2/` y evaluar si las gráficas son correctas.
- *Respuesta:* El script `generate_m2.py` solo importaba `cargar_audio` y generaba una única gráfica por sala (forma de onda). Se identificaron dos problemas: (1) las IRs son estéreo y el `plt.plot` graficaba los dos canales superpuestos (azul y naranja) sin conversión a mono, (2) faltaban las gráficas de decaimiento logarítmico (`a_escala_log`) y decaimiento por banda de octava (`filtro_octava` + `a_escala_log`), que son las funciones centrales de M2.

---

**3. Corrección de `generate_m2.py`**

- *Prompt:* Modificar el script agregando solo lo necesario, sin reemplazar el código del compañero.
- *Respuesta:* Se hicieron cuatro cambios mínimos: (1) se agregaron los imports de `filtro_octava`, `a_escala_log` y la constante `BANDAS = [125, 250, 500, 1000, 2000, 4000]`, (2) se agregó conversión a mono con `mean(axis=1)` después de cada `cargar_audio`, (3) se agregaron dos bloques de plot por IR (decaimiento logarítmico y decaimiento por banda), (4) se eliminaron los emojis de los `print` que rompían la terminal de Windows con encoding CP1252. Se corrigió también un typo en el nombre del archivo WAV (`elvenden_hall.wav` → `elveden_hall.wav`).

---

**4. Generación de las gráficas**

- *Prompt:* Correr el script.
- *Respuesta:* Se generaron exitosamente 6 imágenes: `ir.png`, `decaimiento_log.png` y `decaimiento_por_banda.png` para cada una de las dos IRs. Las gráficas por banda muestran el comportamiento físicamente esperado: en Elveden Hall los graves (250 Hz) decaen más lento que los agudos (4000 Hz); en Maes Howe el T60 es muy corto (~0.3 s) y la banda de 125 Hz no desarrolla energía apreciable dada las dimensiones del recinto.

---

**5. Creación de `validacion_m2.md`**

- *Prompt:* Crear un archivo markdown de validación similar a `validacion_m1.md`, volcando las gráficas con descripción de por qué funcionan.
- *Respuesta:* Se creó `docs/m2/validacion_m2.md` con una sección por función. Las funciones `sintetizar_ri` y `obtener_ri_desde_sweep` se documentan con referencia a los tests automatizados (no gráficas), ya que su validación requiere señales sintéticas con parámetros conocidos. Incluye tabla de resumen con estado de cada criterio.

---

**Evaluación:** La discusión sobre el manejo de estéreo fue conceptualmente útil: `cargar_audio` devuelve ambos canales por consigna, pero el script de validación debe convertir a mono antes de pasar la señal al pipeline de procesamiento. La decisión de usar `mean(axis=1)` en lugar de `[:, 0]` es válida para pares estéreo convencionales (como las IRs de OpenAIR), pero no para grabaciones binaurales. Esto se documentó como una decisión a retomar en los routers de M3.

---

## Pendiente para próximas sesiones

- Crear y pushear el tag `v0.2.0` en main
- Iniciar M3 (vence 7/07): `integral_schroeder`, `regresion_lineal`, `calcular_parametros_acusticos`, endpoints FastAPI, informe
