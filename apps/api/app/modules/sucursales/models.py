import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, ConFechas, ConId


class Sucursal(ConId, ConFechas, Base):
    __tablename__ = "sucursales"

    nombre: Mapped[str] = mapped_column(String(80), unique=True)
    direccion: Mapped[str] = mapped_column(String(200), default="")
    activa: Mapped[bool] = mapped_column(default=True)


class Zona(ConId, ConFechas, Base):
    """Zona de reparto dentro de una sucursal: agrupa clientes y separa listas de precio."""

    __tablename__ = "zonas"
    __table_args__ = (UniqueConstraint("sucursal_id", "nombre"),)

    sucursal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sucursales.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(80))
    activa: Mapped[bool] = mapped_column(default=True)
