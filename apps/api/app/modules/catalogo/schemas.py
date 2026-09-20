import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.schemas import Importe
from app.domain.precios import Lista, Turno


class ProductoSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    codigo: str
    nombre: str
    descripcion: str
    orden: int
    activo: bool


class ProductoCambios(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=60)
    descripcion: str | None = Field(default=None, max_length=200)
    orden: int | None = None
    activo: bool | None = None


class PrecioListaEntrada(BaseModel):
    producto_codigo: str
    lista: Lista
    turno: Turno
    zona_id: uuid.UUID | None = None
    precio: Decimal = Field(gt=0, le=1_000_000, decimal_places=2)


class ListasEntrada(BaseModel):
    sucursal_id: uuid.UUID
    precios: list[PrecioListaEntrada] = Field(min_length=1, max_length=500)


class PrecioListaSalida(BaseModel):
    id: uuid.UUID
    sucursal_id: uuid.UUID
    producto_codigo: str
    lista: Lista
    turno: Turno
    zona_id: uuid.UUID | None
    precio: Importe
