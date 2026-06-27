---
name: project-m3-status
description: Estado del Milestone 3 de RIR-API — funciones DSP y API REST implementadas, 57/57 tests pasando
metadata:
  type: project
---

M3 completamente implementado. 57/57 tests en verde.

**Why:** M3 vence el 7 de julio 2026. Requiere funciones de análisis acústico + API REST completa + tests.

**How to apply:** El proyecto está listo para pruebas de validación con REW y para el informe final.

## Lo implementado en M3

### Servicios (`app/services/acoustic_parameters.py`)
- `suavizar_signal(signal, ventana)` — Hilbert o media móvil
- `integral_schroeder(ri)` — curva de decaimiento en dB normalizada a 0 dB
- `regresion_lineal(x, y)` — mínimos cuadrados manual, retorna `(pendiente, ordenada, R²)`
- `calcular_parametros_acusticos(ri, fs)` — EDT, T10, T20, T30, D50, C80 por banda ISO 3382

### API REST (routers)
- `app/routers/signals.py` → `/api/v1/signals/{pink-noise, sine-sweep, synthetic-ir}`
- `app/routers/filters.py` → `/api/v1/filters/{frequencies, band}`
- `app/routers/acoustics.py` → `/api/v1/acoustics/{parameters, parameters/by-bands}`
- `app/routers/analysis.py` → `/api/v1/analysis/impulse-response`
- `app/routers/utils.py` → `/api/v1/utils/{schroeder, smoothing, log-scale}`

### Fix importante en M2
`filtro_octava` cambiado de `butter()+filtfilt()` a `butter(output='sos')+sosfiltfilt()` para evitar inestabilidad numérica en bandas bajas (125 Hz con fs=44100).

### Schemas
- `app/schemas/signals.py` — PinkNoiseRequest, SineSweepRequest, SyntheticIRRequest
- `app/schemas/responses.py` — respuestas de análisis y utilidades

### Pendiente para entrega final
- Validación con REW (tabla comparativa en docs/m3/)
- Informe final en Quarto/LaTeX
- Tag `v1.0.0` en main
- Release en GitHub con changelog
