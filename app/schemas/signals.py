"""Schemas Pydantic para los endpoints de generacion de senales."""

from pydantic import BaseModel, Field


class PinkNoiseRequest(BaseModel):
    """Parametros para generar ruido rosa."""

    duracion: float = Field(default=5.0, ge=0.1, le=60.0, description="Duracion en segundos")
    fs: int = Field(default=44100, ge=8000, le=192000, description="Frecuencia de muestreo en Hz")


class SineSweepRequest(BaseModel):
    """Parametros para generar un sine sweep logaritmico."""

    f1: float = Field(default=20.0, ge=1.0, le=20000.0, description="Frecuencia inicial en Hz")
    f2: float = Field(default=20000.0, ge=100.0, le=96000.0, description="Frecuencia final en Hz")
    duracion: float = Field(default=5.0, ge=0.1, le=60.0, description="Duracion en segundos")
    fs: int = Field(default=44100, ge=8000, le=192000, description="Frecuencia de muestreo en Hz")


class SyntheticIRRequest(BaseModel):
    """Parametros para generar una respuesta al impulso sintetica."""

    t60_por_banda: dict[str, float] = Field(
        default={
            "125": 2.0,
            "250": 2.0,
            "500": 2.0,
            "1000": 2.0,
            "2000": 2.0,
            "4000": 2.0,
        },
        description="T60 en segundos por banda de octava. Claves: frecuencia central en Hz.",
    )
    fs: int = Field(default=44100, ge=8000, le=192000, description="Frecuencia de muestreo en Hz")
    duracion: float = Field(
        default=3.0, ge=0.1, le=30.0, description="Duracion de la RI en segundos"
    )
