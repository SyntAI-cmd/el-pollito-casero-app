import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, ConFechas, ConId
from app.core.tipos import IMPORTE, JSON_FLEX, FechaHora, enum_sql


class TipoComprobante(StrEnum):
    COMPROBANTE = "comprobante"  # transferencia o cheque
    REMITO_FIRMADO = "remito_firmado"


class Pago(ConId, ConFechas, Base):
    """Un cobro, mixto o no: `partes` guarda [{medio, importe, comprobante_id}]."""

    __tablename__ = "pagos"

    sucursal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sucursales.id"), index=True)
    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clientes.id"), index=True)
    pedido_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pedidos.id"), index=True)
    cobrado_por: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), index=True)
    fecha: Mapped[datetime] = mapped_column(FechaHora, index=True)
    total: Mapped[Decimal] = mapped_column(IMPORTE)
    partes: Mapped[list[dict[str, Any]]] = mapped_column(JSON_FLEX, default=list)
    pedidos_cubiertos: Mapped[list[str]] = mapped_column(JSON_FLEX, default=list)
    saldo_a_favor_usado: Mapped[Decimal] = mapped_column(IMPORTE, default=Decimal("0"))
    nota: Mapped[str] = mapped_column(String(200), default="")
    # Id generada en el celular: el servidor ignora el duplicado si el reintento llega dos veces.
    idempotencia: Mapped[uuid.UUID] = mapped_column(unique=True)


class Comprobante(ConId, Base):
    __tablename__ = "comprobantes"

    sucursal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sucursales.id"), index=True)
    pedido_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pedidos.id"), index=True)
    pago_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pagos.id"), index=True)
    tipo: Mapped[TipoComprobante] = mapped_column(enum_sql(TipoComprobante, "tipo_comprobante"))
    clave_storage: Mapped[str] = mapped_column(String(300))
    tamano_bytes: Mapped[int] = mapped_column(default=0)
    subido_por: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"))
    creado_en: Mapped[datetime] = mapped_column(FechaHora)


class CierreCaja(ConId, Base):
    """Por persona y día: efectivo esperado vs. recibido. Transferencias y cheques van aparte."""

    __tablename__ = "cierres_caja"
    __table_args__ = (UniqueConstraint("usuario_id", "fecha"),)

    sucursal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sucursales.id"), index=True)
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), index=True)
    fecha: Mapped[date] = mapped_column(Date, index=True)
    efectivo_esperado: Mapped[Decimal] = mapped_column(IMPORTE)
    efectivo_recibido: Mapped[Decimal] = mapped_column(IMPORTE)
    transferencias: Mapped[Decimal] = mapped_column(IMPORTE)
    cheques: Mapped[Decimal] = mapped_column(IMPORTE)
    diferencia: Mapped[Decimal] = mapped_column(IMPORTE)
    nota: Mapped[str] = mapped_column(String(300), default="")
    cerrado_por: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"))
    cerrado_en: Mapped[datetime] = mapped_column(FechaHora)


class TipoAjuste(StrEnum):
    REINTEGRO = "reintegro"  # pedido pagado y borrado: lo cobrado vuelve como saldo a favor
    REPESADA = "repesada"  # diferencia por repesar o cambiar precios en un pedido ya pagado
    MANUAL = "manual"  # saldo inicial, arreglos
    USO_SALDO = "uso_saldo"  # saldo a favor aplicado a un cobro


class AjusteCuenta(ConId, Base):
    """
    Movimientos de cuenta corriente que no son pedidos ni pagos. Junto con esos dos, el extracto
    se reconstruye siempre desde acá: no hay tabla de saldos que se desincronice.
    """

    __tablename__ = "ajustes_cuenta"

    sucursal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sucursales.id"), index=True)
    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clientes.id"), index=True)
    fecha: Mapped[datetime] = mapped_column(FechaHora, index=True)
    tipo: Mapped[TipoAjuste] = mapped_column(enum_sql(TipoAjuste, "tipo_ajuste"))
    importe: Mapped[Decimal] = mapped_column(IMPORTE)  # con signo: + deuda, − crédito
    motivo: Mapped[str] = mapped_column(String(200), default="")
    referencia: Mapped[str | None] = mapped_column(String(64))
    registrado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
