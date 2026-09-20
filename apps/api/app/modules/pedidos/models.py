import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, ConFechas, ConId
from app.core.tipos import IMPORTE, JSON_FLEX, KILOS, FechaHora, enum_sql
from app.domain.pedidos import Estado
from app.domain.precios import Turno


class Contador(Base):
    """Correlativos del sistema (hoy solo "remito"). Se lee con FOR UPDATE dentro de la transacción
    que crea el pedido, así dos cargas simultáneas nunca comparten número."""

    __tablename__ = "contadores"

    nombre: Mapped[str] = mapped_column(String(30), primary_key=True)
    valor: Mapped[int] = mapped_column(default=0)


class Pedido(ConId, ConFechas, Base):
    """El número de pedido ES el número de remito: correlativo de 5 dígitos, único en el sistema."""

    __tablename__ = "pedidos"

    numero: Mapped[int] = mapped_column(unique=True)
    sucursal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sucursales.id"), index=True)
    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clientes.id"), index=True)
    preventista_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"), index=True)
    segundo_preventista_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    vehiculo_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("vehiculos.id"))
    salida_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("salidas.id"), index=True)
    zona_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("zonas.id"))
    turno: Mapped[Turno] = mapped_column(enum_sql(Turno, "turno"))
    fecha_reparto: Mapped[date] = mapped_column(Date, index=True)
    estado: Mapped[Estado] = mapped_column(
        enum_sql(Estado, "estado_pedido"), default=Estado.RECIBIDO
    )
    a_cuenta: Mapped[bool] = mapped_column(default=False)  # va a la cuenta corriente
    pagado: Mapped[bool] = mapped_column(default=False)
    subtotal: Mapped[Decimal] = mapped_column(IMPORTE, default=Decimal("0"))
    estimado: Mapped[Decimal] = mapped_column(IMPORTE, default=Decimal("0"))
    total: Mapped[Decimal] = mapped_column(IMPORTE, default=Decimal("0"))
    observaciones: Mapped[str] = mapped_column(String(500), default="")
    creado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    pesado_en: Mapped[datetime | None] = mapped_column(FechaHora)
    entregado_en: Mapped[datetime | None] = mapped_column(FechaHora)
    cancelado_en: Mapped[datetime | None] = mapped_column(FechaHora)
    motivo_cancelacion: Mapped[str | None] = mapped_column(String(200))
    datos: Mapped[dict[str, Any]] = mapped_column(JSON_FLEX, default=dict)

    items: Mapped[list["PedidoItem"]] = relationship(
        back_populates="pedido", cascade="all, delete-orphan", order_by="PedidoItem.orden"
    )


class PedidoItem(ConId, Base):
    __tablename__ = "pedido_items"
    __table_args__ = (UniqueConstraint("pedido_id", "producto_id"),)

    pedido_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pedidos.id", ondelete="CASCADE"))
    producto_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("productos.id"))
    orden: Mapped[int] = mapped_column(default=0)
    cajas: Mapped[int | None] = mapped_column()
    kg_pedidos: Mapped[Decimal | None] = mapped_column(KILOS)
    kg_pesados: Mapped[Decimal | None] = mapped_column(KILOS)
    precio: Mapped[Decimal | None] = mapped_column(IMPORTE)
    precio_propio: Mapped[bool] = mapped_column(default=False)
    importe: Mapped[Decimal] = mapped_column(IMPORTE, default=Decimal("0"))

    pedido: Mapped[Pedido] = relationship(back_populates="items")


class PedidoEvento(ConId, Base):
    """Historia del pedido: cambios de estado, precios, pesada, cobro. Base del extracto."""

    __tablename__ = "pedido_eventos"

    pedido_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pedidos.id", ondelete="CASCADE"), index=True
    )
    tipo: Mapped[str] = mapped_column(String(40))
    detalle: Mapped[dict[str, Any]] = mapped_column(JSON_FLEX, default=dict)
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    creado_en: Mapped[datetime] = mapped_column(FechaHora)
