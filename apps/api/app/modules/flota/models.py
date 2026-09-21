import uuid
from datetime import date, datetime, time

from sqlalchemy import Date, ForeignKey, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, ConFechas, ConId
from app.core.tipos import FechaHora


class Vehiculo(ConId, ConFechas, Base):
    __tablename__ = "vehiculos"

    sucursal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sucursales.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(60))
    patente: Mapped[str] = mapped_column(String(10), unique=True)
    nota: Mapped[str] = mapped_column(String(120), default="")
    activo: Mapped[bool] = mapped_column(default=True)


class Salida(ConId, ConFechas, Base):
    """Un vehículo + hasta dos preventistas + hora de salida, por día."""

    __tablename__ = "salidas"
    __table_args__ = (UniqueConstraint("vehiculo_id", "fecha"),)

    sucursal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sucursales.id"), index=True)
    vehiculo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehiculos.id"))
    fecha: Mapped[date] = mapped_column(Date, index=True)
    hora_salida: Mapped[time | None] = mapped_column(Time)
    preventista_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"))
    segundo_preventista_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    cerrada_en: Mapped[datetime | None] = mapped_column(FechaHora)
    motivo_cierre: Mapped[str | None] = mapped_column(String(200))
