import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, ConFechas, ConId
from app.core.seguridad import Rol
from app.core.tipos import FechaHora, enum_sql


class Usuario(ConId, ConFechas, Base):
    __tablename__ = "usuarios"

    sucursal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sucursales.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(100))
    usuario: Mapped[str] = mapped_column(String(40), unique=True)
    telefono: Mapped[str | None] = mapped_column(String(20))
    cuit: Mapped[str | None] = mapped_column(String(13))
    clave_hash: Mapped[str] = mapped_column(String(200))
    rol: Mapped[Rol] = mapped_column(enum_sql(Rol, "rol"))
    activo: Mapped[bool] = mapped_column(default=True)


class SesionRefresh(ConId, Base):
    """Un refresh token por sesión; revocar la fila cierra la sesión aunque el JWT siga vigente."""

    __tablename__ = "sesiones_refresh"

    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), index=True)
    expira_en: Mapped[datetime] = mapped_column(FechaHora)
    revocado_en: Mapped[datetime | None] = mapped_column(FechaHora)
    creado_en: Mapped[datetime] = mapped_column(FechaHora)


class TokenPush(ConId, Base):
    """Token de push de Expo por dispositivo. Un usuario puede tener varios (celular y tablet)."""

    __tablename__ = "tokens_push"

    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), index=True)
    token: Mapped[str] = mapped_column(String(200), unique=True)
    plataforma: Mapped[str] = mapped_column(String(20), default="")
    actualizado_en: Mapped[datetime] = mapped_column(FechaHora)
