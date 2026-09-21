import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.schemas import Importe
from app.domain.pagos import Medio
from app.domain.saldos import TipoMovimiento
from app.modules.cobros.models import TipoAjuste, TipoComprobante


class ParteEntrada(BaseModel):
    medio: Medio
    importe: Decimal = Field(gt=0, le=100_000_000, decimal_places=2)
    comprobante_id: uuid.UUID | None = None


class PagoEntrada(BaseModel):
    """`pedido_id` presente = cobro en la entrega por el total; ausente = pago a cuenta."""

    idempotencia: uuid.UUID  # generada en el celular: el reintento no duplica el cobro
    cliente_id: uuid.UUID
    pedido_id: uuid.UUID | None = None
    partes: list[ParteEntrada] = Field(min_length=1, max_length=6)
    nota: str = Field(default="", max_length=200)


class ParteSalida(BaseModel):
    medio: Medio
    importe: Importe
    comprobante_id: uuid.UUID | None


class PagoSalida(BaseModel):
    id: uuid.UUID
    cliente_id: uuid.UUID
    cliente_nombre: str
    pedido_id: uuid.UUID | None
    fecha: datetime
    total: Importe
    partes: list[ParteSalida]
    pedidos_cubiertos: list[str]
    saldo_a_favor_usado: Importe
    nota: str
    cobrado_por: uuid.UUID
    cobrado_por_nombre: str


class ComprobanteSalida(BaseModel):
    id: uuid.UUID
    pedido_id: uuid.UUID | None
    pago_id: uuid.UUID | None
    tipo: TipoComprobante
    url: str
    creado_en: datetime


class LineaExtracto(BaseModel):
    fecha: datetime
    tipo: TipoMovimiento
    importe: Importe
    saldo: Importe
    referencia: str
    detalle: str


class ExtractoSalida(BaseModel):
    cliente_id: uuid.UUID
    saldo: Importe  # + deuda, − a favor
    saldo_a_favor: Importe
    pedidos_pendientes: int
    envases: int
    lineas: list[LineaExtracto]


class AjusteEntrada(BaseModel):
    importe: Decimal = Field(decimal_places=2)  # con signo: + deuda, − crédito
    motivo: str = Field(min_length=3, max_length=200)
    fecha: datetime | None = None


class AjusteSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    fecha: datetime
    tipo: TipoAjuste
    importe: Importe
    motivo: str


class CuentaACobrar(BaseModel):
    cliente_id: uuid.UUID
    nombre: str
    direccion: str
    telefono: str | None
    zona_id: uuid.UUID | None
    saldo: Importe
    pedidos_pendientes: int
    ultimo_pago: datetime | None


class CierreEntrada(BaseModel):
    usuario_id: uuid.UUID | None = None  # None = el que cierra su propia caja
    fecha: date
    efectivo_recibido: Decimal = Field(ge=0, decimal_places=2)
    nota: str = Field(default="", max_length=300)


class CierreSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    usuario_id: uuid.UUID
    fecha: date
    efectivo_esperado: Importe
    efectivo_recibido: Importe
    transferencias: Importe
    cheques: Importe
    diferencia: Importe
    nota: str
    cerrado_por: uuid.UUID
    cerrado_en: datetime


class ResumenCaja(BaseModel):
    usuario_id: uuid.UUID
    usuario_nombre: str
    fecha: date
    efectivo_esperado: Importe
    transferencias: Importe
    cheques: Importe
    total_cobrado: Importe
    cantidad_cobros: int
    pagos: list[PagoSalida]
    cierre: CierreSalida | None
