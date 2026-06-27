"""RIR-API - Room Impulse Response API.

Punto de entrada de la aplicacion FastAPI.

Uso:
    uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import acoustics, analysis, convolution, filters, health, signals, utils

app = FastAPI(
    title="RIR-API",
    description=(
        "API REST para procesamiento y analisis de respuestas al impulso segun ISO 3382. "
        "Incluye generacion de senales (M1), procesamiento de RI (M2) y "
        "calculo de parametros acusticos EDT, T10, T20, T30, D50 y C80 (M3)."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(signals.router, prefix="/api/v1/signals", tags=["signals"])
app.include_router(filters.router, prefix="/api/v1/filters", tags=["filters"])
app.include_router(acoustics.router, prefix="/api/v1/acoustics", tags=["acoustics"])
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["analysis"])
app.include_router(utils.router, prefix="/api/v1/utils", tags=["utils"])
app.include_router(convolution.router, prefix="/api/v1/convolution", tags=["convolution"])


@app.get("/", tags=["root"])
async def root() -> dict:
    """Informacion basica de la API."""
    return {
        "name": "RIR-API",
        "version": "1.0.0",
        "description": "Room Impulse Response API — ISO 3382",
        "docs": "/docs",
        "redoc": "/redoc",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
