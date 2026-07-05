# Documentacion de RIR-API

## Estructura

Este directorio contiene la documentacion del proyecto, organizada por milestone:

```
docs/
├── README.md              # Este archivo
├── informe.md              # Informe tecnico final (Resumen, Marco teorico,
│                            # Desarrollo experimental, Resultados, Conclusiones)
├── IA.md                   # Log de interacciones con asistentes de IA
├── m0/
│   └── m0_consigna.md       # Consigna del Milestone 0 (planificacion)
├── m1/                      # Milestone 1 — Generacion de senales
│   ├── m1_consigna.md
│   ├── validacion_m1.md      # Validacion de ruido rosa, sine sweep y convolucion
│   ├── scripts/             # Scripts que generan los graficos de validacion
│   └── imagenes/            # Graficos de validacion (PSD, espectrogramas, convolucion)
├── m2/                      # Milestone 2 — Procesamiento de la RI
│   ├── m2_consigna.md
│   ├── validacion_m2.md      # Validacion de carga de audio, filtros y deconvolucion
│   ├── scripts/
│   ├── imagenes/
│   ├── mediciones/          # RIs propias medidas con medir_ri.py
│   ├── elveden_hall/        # RI de OpenAIR (sala grande)
│   └── maes_howe/           # RI de OpenAIR (camara pequeña)
└── m3/                      # Milestone 3 — Analisis acustico y validacion
    ├── m3_consigna.md
    ├── validacion_m3.md      # Validacion detallada contra REW
    ├── scripts/
    ├── Imagenes/
    └── tablas_validacion/    # Exportaciones de REW y CSVs de comparacion
```

## API de referencia

Se tomó como referencia la API de la cátedra de Señales y Sistemas de la UNTREF: [documentacion interactiva de la API de la catedra](https://rir-api.onrender.com/docs)
para entender la estructura de endpoints, schemas y respuestas esperadas.

## Referencias utiles

- **ISO 3382-1:2009** — [Acoustics — Measurement of room acoustic parameters](https://www.iso.org/standard/40979.html).
- **IEC 61260-1:2014** — Electroacoustics — Octave-band and fractional-octave-band filters.
- Farina, A. (2000). *Simultaneous measurement of impulse response and distortion
  with a swept-sine technique.* 108th AES Convention.
- Schroeder, M. R. (1965). [New method of measuring reverberation time](https://asa.scitation.org/doi/10.1121/1.1909343).
  *The Journal of the Acoustical Society of America*, 37(3), 409–412.
- Lundeby, A. et al. (1995). [Uncertainties of measurements in room acoustics](https://doi.org/10.1155/1995/37816).
  *Acustica*, 81(4), 344–355.
- Welch, P. D. (1967). *The use of fast Fourier transform for the estimation of power spectra.*
  IEEE Transactions on Audio and Electroacoustics, 15(2), 70–73.
- Butterworth, S. (1930). *On the theory of filter amplifiers.* Experimental Wireless
  and the Wireless Engineer, 7, 536–541.
- Voss, R. F., & Clarke, J. (1978). *"1/f noise" in music: Music from 1/f noise.*
  The Journal of the Acoustical Society of America, 63(1), 258–263.
- [FastAPI: documentacion oficial](https://fastapi.tiangolo.com/)
- [Pydantic: validacion de datos](https://docs.pydantic.dev/)
- [scipy.signal.hilbert](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.hilbert.html)
- [REW — Room EQ Wizard](https://www.roomeqwizard.com/)
