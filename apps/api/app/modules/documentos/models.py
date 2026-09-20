import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, ConId
from app.core.tipos import JSON_FLEX, FechaHora, enum_sql


class TipoDocumento(StrEnum):
    REMITOS = "remitos"  # PDF, 4 por hoja A4
    HOJA_PEDIDOS = "hoja_pedidos"  # PDF A4 apaisada por turno y preventista
    HOJA_RUTA = "hoja_ruta"  # PDF hoja de ruta y rendición por preventista
    TICKETS = "tickets"  # PDF para comandera de 80 mm
    CONSOLIDADO = "consolidado"  # Excel del día


class EstadoDocumento(StrEnum):
    PENDIENTE = "pendiente"
    LISTO = "listo"
    ERROR = "error"


class Documento(ConId, Base):
    """PDF o Excel generado en el worker y archivado en storage."""

    __tablename__ = "documentos"

    sucursal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sucursales.id"), index=True)
    tipo: Mapped[TipoDocumento] = mapped_column(enum_sql(TipoDocumento, "tipo_documento"))
    parametros: Mapped[dict[str, Any]] = mapped_column(JSON_FLEX, default=dict)
    estado: Mapped[EstadoDocumento] = mapped_column(
        enum_sql(EstadoDocumento, "estado_documento"), default=EstadoDocumento.PENDIENTE
    )
    clave_storage: Mapped[str | None] = mapped_column(String(300))
    nombre_archivo: Mapped[str] = mapped_column(String(120), default="")
    error: Mapped[str | None] = mapped_column(String(300))
    creado_por: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"))
    creado_en: Mapped[datetime] = mapped_column(FechaHora)
    listo_en: Mapped[datetime | None] = mapped_column(FechaHora)
