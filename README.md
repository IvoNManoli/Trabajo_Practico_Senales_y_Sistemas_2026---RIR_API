# RIR-API

API REST para procesamiento y análisis de respuestas al impulso según la norma ISO 3382.

## Descripción

RIR-API es un proyecto educativo que implementa una API REST (FastAPI) con una cadena completa de procesamiento acústico: generación de señales de excitación, procesamiento de respuestas al impulso por bandas de octava y cálculo de parámetros acústicos (EDT, T20, T30) según la norma ISO 3382-1.

## Integrantes

- Ivo Manoli
    - Legajo 64189
    - Responsable de procesamiento y 
    generación de señales

- Gaspar Dallinge
    - Legajo 62751
    - Responsable de testing/CI y documentación

## Instalación

```bash
# Clonar el repositorio
git clone https://github.com/IvoNManoli/Trabajo_Practico_Senales_y_Sistemas_2026---RIR_API
cd trabajo_practico/RIR-API

# Crear entorno virtual e instalar dependencias
uv sync
uv pip install -e ".[dev]"
```

## Ejecución

```bash
# Iniciar la API con hot-reload
uv run uvicorn app.main:app --reload
```

La API estara disponible en `http://localhost:8000`. Documentación interactiva en:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Estructura del proyecto

```
RIR-API/
├── app/
│   ├── main.py                        # Punto de entrada FastAPI
│   ├── routers/
│   │   ├── health.py                  # GET /health
│   │   ├── signals.py                 # Generación de señales (M1)
│   │   ├── filters.py                 # Filtrado por banda de octava (M2)
│   │   ├── acoustics.py               # Parámetros acústicos ISO 3382 (M3)
│   │   ├── analysis.py                # Análisis completo de RI (M3)
│   │   ├── convolution.py             # Convolución de RI con audio (M3)
│   │   └── utils.py                   # Schroeder, suavizado, log-scale
│   ├── schemas/
│   │   ├── signals.py                 # Schemas de request para señales
│   │   └── responses.py               # Schemas de respuesta para análisis
│   └── services/
│       ├── pink_noise.py              # Generación de ruido rosa (M1)
│       ├── sine_sweep.py              # Generación de sine sweep (M1)
│       ├── signal_utils.py            # Carga, síntesis y deconvolución de RI (M2)
│       ├── filter.py                  # Filtros de banda de octava (M2)
│       ├── grabacion_utils.py         # Reproducción y grabación de audio (M2)
│       ├── acoustic_parameters.py     # EDT, T10, T20, T30, D50, C80, Lundeby (M3)
│       └── convolution.py             # Convolución de RI con audio (M3)
├── tests/
│   ├── test_generacion.py             # Tests de generación de señales (M1)
│   ├── test_procesamiento.py          # Tests de procesamiento de RI (M2)
│   ├── test_analisis.py               # Tests de parámetros acústicos (M3)
│   └── test_api.py                    # Tests de endpoints HTTP (M3)
├── docs/                          # Documentación
├── .github/workflows/ci.yml       # Integración continua
├── pyproject.toml                 # Configuración del proyecto
└── README.md
```
## Diagrama de arquitectura
```mermaid
graph LR
    Client -->|HTTP| R

    subgraph R[Routers]
        r1[health]
        r2[signals]
        r3[filters]
        r4[acoustics]
        r5[analysis]
        r6[convolution]
        r7[utils]
    end

    subgraph M1[Services · M1]
        s1[pink_noise]
        s2[sine_sweep]
    end

    subgraph M2[Services · M2]
        s3[signal_utils]
        s4[filter]
        s5[grabacion_utils]
    end

    subgraph M3[Services · M3]
        s6[acoustic_parameters]
        s7[convolution]
    end

    r2 --> s1 & s2 & s3
    r3 --> s4
    r4 --> s6
    r5 --> s3 & s6
    r6 --> s7
    r7 --> s6
```

## Dependencias Externas

```
R --> FastAPI[FastAPI]              # Entrada del sistema
R --> Uvicorn[Uvicorn]              # Ejecuta la app FastAPI
Sch --> Pydantic[Pydantic]          # Validación de datos
S --> NumPy[NumPy]                  # Arrays, operaciones matemáticas
S --> SciPy[SciPy]                  # Filtros, deconvolución
S --> Audio[sounddevice]            # Captura y reproduce audio
S --> Matplotlib[Matplotlib]        # Gráficos
```

## Estrategia de ramas

- main:  
  Esta es la rama principal del proyecto. Contiene el código que está listo para producción. Solo se hacen merge a esta rama mediante Pull Requests. Cualquier cambio importante o funcionalidad nueva debe pasar por una revisión de código antes de ser fusionado en main.

- feature/generacion-de-señales:
  Esta rama es responsable de la generación de señales de excitación para la respuesta al impulso (RIR).
  Responsable: Ivo Manoli

- feature/procesamiento-de-RI:  
  Esta rama es responsable del procesamiento de las respuestas al impulso (RI) para obtener los parámetros acústicos necesarios según la norma ISO 3382.
  Responsable: Ivo Manoli

- feature/testing-ci:  
  Esta rama se dedicará a la implementación de pruebas automáticas (unitarias y de integración) y la configuración de la integración continua (CI) del proyecto.  
  Responsable: Gaspar Dallinge

- feature/documentacion:  
  Esta rama será utilizada para escribir y mantener la documentación del proyecto, como el README.md y la documentación técnica de la API.  
  Responsable: Gaspar Dallinge
