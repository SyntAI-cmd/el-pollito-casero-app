import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.schemas import Kilos


class CajonEntrada(BaseModel):
    """Un cajón. La id la genera el celular para que un reintento offline no duplique."""

    id: uuid.UUID
    producto_codigo: str
    bruto: Decimal = Field(gt=0, le=5000, decimal_places=3)
    pesado_en: datetime | None = None  # cuándo se pesó de verdad, si llega en diferido


class LoteEntrada(BaseModel):
    """N cajas con un solo bruto total. Las ids de los cajones se derivan de `lote_id`."""

    lote_id: uuid.UUID
    producto_codigo: str
    cajas: int = Field(ge=1, le=500)
    bruto_total: Decimal = Field(gt=0, le=5000, decimal_places=3)
    pesado_en: datetime | None = None


class AnulacionEntrada(BaseModel):
    motivo: str = Field(min_length=3, max_length=200)


class CajonSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pedido_id: uuid.UUID
    producto_codigo: str
    bruto: Kilos
    tara: Kilos
    neto: Kilos
    cargado: bool
    cargado_en: datetime | None
    anulado: bool
    motivo_anulacion: str | None
    pesado_en: datetime
