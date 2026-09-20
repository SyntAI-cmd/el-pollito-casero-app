import uuid
from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class VehiculoEntrada(BaseModel):
    sucursal_id: uuid.UUID | None = None
    nombre: str = Field(min_length=2, max_length=60)
    patente: str = Field(min_length=5, max_length=10)
    nota: str = Field(default="", max_length=120)


class VehiculoCambios(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=60)
    patente: str | None = Field(default=None, min_length=5, max_length=10)
    nota: str | None = Field(default=None, max_length=120)
    activo: bool | None = None


class VehiculoSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sucursal_id: uuid.UUID
    nombre: str
    patente: str
    nota: str
    activo: bool


class SalidaEntrada(BaseModel):
    """Alta o actualización de la salida del día para un vehículo."""

    vehiculo_id: uuid.UUID
    fecha: date
    preventista_id: uuid.UUID
    segundo_preventista_id: uuid.UUID | None = None
    hora_salida: time | None = None


class CierreEntrada(BaseModel):
    motivo: str | None = Field(default=None, max_length=200)


class PosicionEntrada(BaseModel):
    lat: Decimal = Field(ge=-90, le=90, decimal_places=6)
    lng: Decimal = Field(ge=-180, le=180, decimal_places=6)
    velocidad: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    registrado_en: datetime | None = None


class PosicionSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    lat: Decimal
    lng: Decimal
    velocidad: Decimal | None
    registrado_en: datetime


class FaltanteSalida(BaseModel):
    pedido_id: uuid.UUID
    numero: str
    sin_pesar: int
    sin_cargar: int


class SalidaSalida(BaseModel):
    id: uuid.UUID
    sucursal_id: uuid.UUID
    vehiculo_id: uuid.UUID
    vehiculo_nombre: str
    vehiculo_patente: str
    fecha: date
    hora_salida: time | None
    preventista_id: uuid.UUID
    preventista_nombre: str
    segundo_preventista_id: uuid.UUID | None
    segundo_preventista_nombre: str | None
    cerrada_en: datetime | None
    motivo_cierre: str | None
    pedidos: int
    pedidos_entregados: int
    ultima_posicion: PosicionSalida | None
    faltantes: list[FaltanteSalida]
