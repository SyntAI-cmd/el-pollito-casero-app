import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.tipos import KILOS, FechaHora


class Cajon(Base):
    """Una fila por cajón pesado. La id la genera el celular: un reintento no duplica."""

    __tablename__ = "cajones"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    sucursal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sucursales.id"), index=True)
    pedido_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pedidos.id", ondelete="CASCADE"), index=True
    )
    producto_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("productos.id"))
    bruto: Mapped[Decimal] = mapped_column(KILOS)
    tara: Mapped[Decimal] = mapped_column(KILOS)
    neto: Mapped[Decimal] = mapped_column(KILOS)
    cargado: Mapped[bool] = mapped_column(default=False)
    cargado_en: Mapped[datetime | None] = mapped_column(FechaHora)
    anulado: Mapped[bool] = mapped_column(default=False)
    motivo_anulacion: Mapped[str | None] = mapped_column(String(200))
    pesado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    pesado_en: Mapped[datetime] = mapped_column(FechaHora)
