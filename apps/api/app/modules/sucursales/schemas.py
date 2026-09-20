import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.schemas import Kilos


class SucursalEntrada(BaseModel):
    nombre: str = Field(min_length=2, max_length=80)
    direccion: str = Field(default="", max_length=200)


class SucursalCambios(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=80)
    direccion: str | None = Field(default=None, max_length=200)
    tara: Decimal | None = Field(default=None, ge=0, le=20, decimal_places=3)
    activa: bool | None = None


class SucursalSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    direccion: str
    tara: Kilos
    activa: bool


class ZonaEntrada(BaseModel):
    nombre: str = Field(min_length=2, max_length=80)


class ZonaCambios(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=80)
    activa: bool | None = None


class ZonaSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sucursal_id: uuid.UUID
    nombre: str
    activa: bool
