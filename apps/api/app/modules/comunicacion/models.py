import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, ConFechas, ConId
from app.core.tipos import FechaHora


class Noticia(ConId, ConFechas, Base):
    """Avisos del equipo que van arriba de la nota del día."""

    __tablename__ = "noticias"

    sucursal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sucursales.id"), index=True)
    autor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"))
    titulo: Mapped[str] = mapped_column(String(120))
    cuerpo: Mapped[str] = mapped_column(Text, default="")
    fijada: Mapped[bool] = mapped_column(default=False)
    archivada: Mapped[bool] = mapped_column(default=False)


class Mensaje(ConId, Base):
    """Chat interno por sucursal."""

    __tablename__ = "mensajes"

    sucursal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sucursales.id"), index=True)
    autor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"))
    cuerpo: Mapped[str] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(FechaHora, index=True)
