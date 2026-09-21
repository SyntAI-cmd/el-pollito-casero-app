import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.schemas import Importe, Kilos
from app.domain.pedidos import Estado
from app.domain.precios import Turno


class ItemEntrada(BaseModel):
    producto_codigo: str
    cajas: int | None = Field(default=None, ge=0, le=500)
    kg: Decimal | None = Field(default=None, gt=0, le=5000, decimal_places=3)
    # Precio tipeado en el momento de cargar; pisa el propio y la lista para este pedido.
    precio: Decimal | None = Field(default=None, gt=0, le=1_000_000, decimal_places=2)
    guardar_precio_propio: bool = False

    @model_validator(mode="after")
    def _cajas_o_kilos(self) -> "ItemEntrada":
        if self.cajas is None and self.kg is None:
            raise ValueError("Indicá cajas o kilos")
        return self


class PedidoEntrada(BaseModel):
    cliente_id: uuid.UUID
    fecha_reparto: date
    turno: Turno
    a_cuenta: bool = False
    preventista_id: uuid.UUID | None = None
    segundo_preventista_id: uuid.UUID | None = None
    vehiculo_id: uuid.UUID | None = None
    zona_id: uuid.UUID | None = None
    observaciones: str = Field(default="", max_length=500)
    items: list[ItemEntrada] = Field(min_length=1, max_length=20)


class PedidoCambios(BaseModel):
    fecha_reparto: date | None = None
    turno: Turno | None = None
    a_cuenta: bool | None = None
    preventista_id: uuid.UUID | None = None
    segundo_preventista_id: uuid.UUID | None = None
    vehiculo_id: uuid.UUID | None = None
    zona_id: uuid.UUID | None = None
    observaciones: str | None = Field(default=None, max_length=500)


class PrecioItemEntrada(BaseModel):
    producto_codigo: str
    precio: Decimal = Field(gt=0, le=1_000_000, decimal_places=2)
    guardar_precio_propio: bool = False


class PreciosPedidoEntrada(BaseModel):
    precios: list[PrecioItemEntrada] = Field(min_length=1, max_length=20)


class EstadoEntrada(BaseModel):
    estado: Estado
    motivo: str | None = Field(default=None, max_length=200)


class ItemSalida(BaseModel):
    producto_codigo: str
    producto_nombre: str
    cajas: int | None
    kg_pedidos: Kilos | None
    kg_pesados: Kilos | None
    precio: Importe | None
    precio_propio: bool
    importe: Importe
    cajones: int
    cajones_cargados: int


class PedidoSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    numero: str
    sucursal_id: uuid.UUID
    cliente_id: uuid.UUID
    cliente_nombre: str
    cliente_direccion: str
    cliente_telefono: str | None
    estado: Estado
    turno: Turno
    fecha_reparto: date
    a_cuenta: bool
    pagado: bool
    subtotal: Importe
    estimado: Importe
    total: Importe
    preventista_id: uuid.UUID | None
    segundo_preventista_id: uuid.UUID | None
    vehiculo_id: uuid.UUID | None
    salida_id: uuid.UUID | None
    zona_id: uuid.UUID | None
    observaciones: str
    items: list[ItemSalida]
    sin_precio: list[str]
    sin_pesar: list[str]
    cajones: int
    cajones_cargados: int
    creado_en: datetime
    pesado_en: datetime | None
    entregado_en: datetime | None
    cancelado_en: datetime | None
    motivo_cancelacion: str | None


class EventoSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tipo: str
    detalle: dict[str, object]
    usuario_id: uuid.UUID | None
    creado_en: datetime


class TotalProducto(BaseModel):
    producto_codigo: str
    producto_nombre: str
    cajas: int
    kg_pedidos: Kilos
    kg_pesados: Kilos
    pedidos: int


class GrupoPreventista(BaseModel):
    preventista_id: uuid.UUID | None
    preventista_nombre: str
    pedidos: list[PedidoSalida]
    cajones: int
    kilos: Kilos
    importe: Importe


class NotaDelDia(BaseModel):
    fecha: date
    turno: Turno | None
    cantidad_pedidos: int
    cajones: int
    kilos: Kilos
    importe: Importe
    por_producto: list[TotalProducto]
    por_preventista: list[GrupoPreventista]
