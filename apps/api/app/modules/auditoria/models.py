import uuid
from typing import Any

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, ConFechas, ConId
from app.core.tipos import JSON_FLEX


class AuditLog(ConId, ConFechas, Base):
    """Toda operación de dinero deja una fila acá, dentro de la misma transacción."""

    __tablename__ = "audit_log"

    sucursal_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    accion: Mapped[str] = mapped_column(String(60), index=True)
    entidad: Mapped[str] = mapped_column(String(40))
    entidad_id: Mapped[str] = mapped_column(String(64), index=True)
    detalle: Mapped[dict[str, Any]] = mapped_column(JSON_FLEX, default=dict)
