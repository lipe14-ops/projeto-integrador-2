from datetime import datetime as DateTimeValue

from pydantic import BaseModel, Field


class RegistroClimaticoResponse(BaseModel):
    datetime: DateTimeValue
    umidade: float | None
    temperatura: float | None
    precipitacao: float | None


class EnsoMensalResponse(BaseModel):
    year: int
    month: int
    enso_index: float | None


class ClimaMunicipioResponse(BaseModel):
    codigo_ibge: int
    registros: list[RegistroClimaticoResponse]
    enso: list[EnsoMensalResponse] = Field(default_factory=list)