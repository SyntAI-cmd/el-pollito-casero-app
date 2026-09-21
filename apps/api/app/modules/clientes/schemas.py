import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.schemas import Importe
from app.domain.precios import Lista, Turno
from app.modules.clientes.models import EstadoFicha


class ClienteEntrada(BaseModel):
    sucursal_id: uuid.UUID | None = None  # None = la del usuario que carga
    codigo: str | None = Field(default=None, max_length=20)
    razon_social: str = Field(min_length=2, max_length=120)
    nombre_comercial: str | None = Field(default=None, min_length=2, max_length=120)
    cuit: str | None = Field(default=None, max_length=13)
    telefono: str | None = Field(default=None, max_length=25)
    direccion: str = Field(default="", max_length=250)
    localidad: str = Field(default="", max_length=80)
    zona_id: uuid.UUID | None = None
    lista: Lista = Lista.MAYORISTA
    turno: Turno = Turno.MANANA
    preventista_id: uuid.UUID | None = None
    cobrador_id: uuid.UUID | None = None
    credito_habilitado: bool = True
    observaciones: str = Field(default="", max_length=500)


class ClienteCambios(BaseModel):
    codigo: str | None = Field(default=None, max_length=20)
    razon_social: str | None = Field(default=None, min_length=2, max_length=120)
    nombre_comercial: str | None = Field(default=None, min_length=2, max_length=120)
    cuit: str | None = Field(default=None, max_length=13)
    telefono: str | None = Field(default=None, max_length=25)
    direccion: str | None = Field(default=None, max_length=250)
    localidad: str | None = Field(default=None, max_length=80)
    zona_id: uuid.UUID | None = None
    lista: Lista | None = None
    turno: Turno | None = None
    preventista_id: uuid.UUID | None = None
    cobrador_id: uuid.UUID | None = None
    credito_habilitado: bool | None = None
    ajuste_envases: int | None = None
    estado_ficha: EstadoFicha | None = None
    observaciones: str | None = Field(default=None, max_length=500)
    activo: bool | None = None


class ClienteSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sucursal_id: uuid.UUID
    codigo: str | None
    razon_social: str
    nombre_comercial: str
    cuit: str | None
    telefono: str | None
    direccion: str
    localidad: str
    zona_id: uuid.UUID | None
    lista: Lista
    turno: Turno
    preventista_id: uuid.UUID | None
    cobrador_id: uuid.UUID | None
    credito_habilitado: bool
    ajuste_envases: int
    estado_ficha: EstadoFicha
    observaciones: str
    activo: bool


class PrecioPropioEntrada(BaseModel):
    producto_codigo: str
    precio: Decimal | None = Field(default=None, gt=0, le=1_000_000, decimal_places=2)


class PreciosPropiosEntrada(BaseModel):
    precios: list[PrecioPropioEntrada] = Field(min_length=1, max_length=50)


class PrecioResuelto(BaseModel):
    producto_codigo: str
    producto_nombre: str
    precio: Importe | None
    origen: str  # "propio" | "lista" | "sin_precio"


class MovimientoEnvasesEntrada(BaseModel):
    dejados: int = Field(default=0, ge=0, le=1000)
    devueltos: int = Field(default=0, ge=0, le=1000)
    nota: str = Field(default="", max_length=200)
    pedido_id: uuid.UUID | None = None


class MovimientoEnvasesSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    fecha: datetime
    dejados: int
    devueltos: int
    nota: str
    pedido_id: uuid.UUID | None


class EnvasesSalida(BaseModel):
    saldo: int
    ajuste: int
    movimientos: list[MovimientoEnvasesSalida]
