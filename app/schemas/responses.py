"""Schemas Pydantic para las respuestas de la API."""

from pydantic import BaseModel


class FrequenciasResponse(BaseModel):
    """Lista de frecuencias centrales disponibles para filtrado."""

    frecuencias: list[float]


class SchroederResponse(BaseModel):
    """Curva de Schroeder de una respuesta al impulso."""

    tiempo: list[float]
    nivel_db: list[float]
    fs: int


class LogScaleResponse(BaseModel):
    """Senal convertida a escala logaritmica (dB)."""

    tiempo: list[float]
    nivel_db: list[float]
    fs: int


class SmoothingResponse(BaseModel):
    """Envolvente suavizada de una senal."""

    tiempo: list[float]
    envolvente: list[float]
    fs: int


class AcousticParametersResponse(BaseModel):
    """Parametros acusticos ISO 3382 por banda de octava."""

    EDT: dict[str, float | None]
    T10: dict[str, float | None]
    T20: dict[str, float | None]
    T30: dict[str, float | None]
    D50: dict[str, float | None]
    C80: dict[str, float | None]
