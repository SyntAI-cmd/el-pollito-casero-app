import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, ConFechas, ConId
from app.core.tipos import IMPORTE, JSON_FLEX, FechaHora, enum_sql
from app.domain.precios import Lista, Turno


class EstadoFicha(StrEnum):
    COMPLETA = "completa"
    SIN_CUIT = "sin_cuit"
    REVISAR = "revisar"


class Cliente(ConId, ConFechas, Base):
    """Ficha al estilo GC/Atuq. El teléfono es índice único opcional, nunca la clave."""

    __tablename__ = "clientes"
    __table_args__ = (UniqueConstraint("sucursal_id", "codigo"),)

    sucursal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sucursales.id"), index=True)
    codigo: Mapped[str | None] = mapped_column(String(20))
    razon_social: Mapped[str] = mapped_column(String(120))
    nombre_comercial: Mapped[str] = mapped_column(String(120))
    cuit: Mapped[str | None] = mapped_column(String(13), index=True)
    telefono: Mapped[str | None] = mapped_column(String(20), unique=True)
    direccion: Mapped[str] = mapped_column(String(250), default="")
    localidad: Mapped[str] = mapped_column(String(80), default="")
    zona_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("zonas.id"), index=True)
    lista: Mapped[Lista] = mapped_column(enum_sql(Lista, "lista_precio"), default=Lista.MAYORISTA)
    turno: Mapped[Turno] = mapped_column(enum_sql(Turno, "turno"), default=Turno.MANANA)
    preventista_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"), index=True)
    cobrador_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"), index=True)
    credito_habilitado: Mapped[bool] = mapped_column(default=True)
    saldo_a_favor: Mapped[Decimal] = mapped_column(IMPORTE, default=Decimal("0"))
    ajuste_envases: Mapped[int] = mapped_column(default=0)
    estado_ficha: Mapped[EstadoFicha] = mapped_column(
        enum_sql(EstadoFicha, "estado_ficha"), default=EstadoFicha.REVISAR
    )
    observaciones: Mapped[str] = mapped_column(String(500), default="")
    activo: Mapped[bool] = mapped_column(default=True)
    datos: Mapped[dict[str, Any]] = mapped_column(JSON_FLEX, default=dict)


class PrecioCliente(ConId, ConFechas, Base):
    """Precio propio por producto: pisa la lista. Sin fila, el renglón queda "sin precio"."""

    __tablename__ = "precios_cliente"
    __table_args__ = (UniqueConstraint("cliente_id", "producto_id"),)

    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clientes.id"), index=True)
    producto_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("productos.id"))
    precio: Mapped[Decimal] = mapped_column(IMPORTE)


class MovimientoEnvases(ConId, Base):
    __tablename__ = "movimientos_envases"

    sucursal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sucursales.id"), index=True)
    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clientes.id"), index=True)
    pedido_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pedidos.id"))
    fecha: Mapped[datetime] = mapped_column(FechaHora)
    dejados: Mapped[int] = mapped_column(default=0)
    devueltos: Mapped[int] = mapped_column(default=0)
    nota: Mapped[str] = mapped_column(String(200), default="")
    registrado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
