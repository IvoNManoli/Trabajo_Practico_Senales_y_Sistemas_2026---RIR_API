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

## Pendiente para próximas sesiones

- Crear tag `v0.1.0` y hacer PR a main
- Iniciar M2 (vence 16/06): `cargar_audio`, `a_escala_log`, `obtener_ri_desde_sweep`, `sintetizar_ri`, `filtro_octava`
