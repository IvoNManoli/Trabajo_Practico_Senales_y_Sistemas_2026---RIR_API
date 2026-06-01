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

### Entrada 1 — Contexto permanente para IA en el proyecto

| Campo | Detalle |
| :--- | :--- |
| **Fecha** | 01/06/2026 |
| **Herramienta** | Claude (claude.ai) |
| **Prompt resumido** | Se pidió armar un archivo de instrucciones para dar contexto permanente del proyecto a herramientas de IA |
| **Resultado** | Se creó `.github/copilot-instructions.md` con stack tecnológico, arquitectura de 3 capas, funciones requeridas por M1 y reglas de código |
| **Evaluación** | Útil para no repetir contexto en cada sesión. Se aprendió que mantener un archivo de contexto actualizado ahorra tiempo y mejora la calidad de las respuestas de la IA |

---

### Entrada 2 — Diagnóstico del estado de M1

| Campo | Detalle |
| :--- | :--- |
| **Fecha** | 01/06/2026 |
| **Herramienta** | Claude (claude.ai) |
| **Prompt resumido** | Se compartió el contenido completo del repositorio y se pidió identificar qué faltaba para completar M1 |
| **Resultado** | Se identificaron 4 problemas: (1) firma incorrecta de `reproducir_y_grabar`, (2) falta del test de convolución sweep × filtro_inverso, (3) falta del tag `v0.1.0`, (4) `ci.yml` apuntando a `src/` en lugar de `app/` |
| **Evaluación** | Diagnóstico preciso y útil. Se modificó el plan de trabajo en base a estos hallazgos. Se aprendió a usar PowerShell para exportar el contenido del repositorio como contexto para la IA |

---

### Entrada 3 — Corrección de firma de `reproducir_y_grabar`

| Campo | Detalle |
| :--- | :--- |
| **Fecha** | 01/06/2026 |
| **Herramienta** | Claude (claude.ai) |
| **Prompt resumido** | Pedir corrección de la firma de `reproducir_y_grabar` para recibir `duracion_grabacion` en lugar de `num_canales`, con manejo de error si no hay dispositivo de audio |
| **Resultado** | Se reemplazó `num_canales: int` por `duracion_grabacion: float`. Se agregó `try/except` que lanza `RuntimeError` si no hay dispositivo disponible. Se renombró el archivo de `grabacion.py` a `grabacion_utils.py` a sugerencia del docente |
| **Evaluación** | El cambio fue correcto y necesario — la firma anterior no coincidía con la especificación de M1. El parámetro `duracion_grabacion` tiene sentido físico real: permite capturar la cola de reverberación después de que termina la señal de excitación. Se verificó con `uv run python -c "from app.services.grabacion_utils import reproducir_y_grabar; print('OK')"` |

---

### Entrada 4 — Test de convolución sweep × filtro_inverso

| Campo | Detalle |
| :--- | :--- |
| **Fecha** | 01/06/2026 |
| **Herramienta** | Claude (claude.ai) |
| **Prompt resumido** | Pedir implementación del test que verifica que sweep × filtro_inverso produce un impulso con pico > 40 dB sobre el piso de ruido |
| **Resultado** | Se implementó `test_convolucion_genera_impulso` en `TestGenerarSineSweep`. Usa `fftconvolve`, encuentra el pico, calcula el piso excluyendo 100 muestras vecinas, y verifica la relación en dB. Resultado: 7/7 tests en verde |
| **Evaluación** | Antes de aceptar el código se entendió el concepto: la convolución del sweep con su filtro inverso debe aproximarse a un delta de Dirac. Esto no es solo un test — es el principio fundamental detrás de la medición de respuestas al impulso que se va a usar en M2 |

---

## Pendiente para próximas sesiones

- Corregir `ci.yml`: cambiar `src/` por `app/` en el paso de ruff
- Crear tag `v0.1.0` para entrega oficial de M1
- Iniciar M2: filtros de banda de octava y deconvolución