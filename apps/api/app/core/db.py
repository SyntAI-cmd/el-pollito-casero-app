import uuid
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Annotated

from fastapi import Depends
from sqlalchemy import MetaData, func
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import get_settings
from app.core.tipos import FechaHora

# Nombres predecibles para que Alembic pueda borrar y renombrar restricciones sin adivinar.
CONVENCION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=CONVENCION)


class ConId:
    """Clave primaria UUID en todas las tablas."""

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class ConFechas:
    """Fechas en TIMESTAMPTZ; la zona se interpreta como America/Argentina/Mendoza al mostrar."""

    creado_en: Mapped[datetime] = mapped_column(
        FechaHora, server_default=func.now(), nullable=False
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        FechaHora, server_default=func.now(), onupdate=func.now(), nullable=False
    )


_engine: AsyncEngine | None = None
_fabrica: async_sessionmaker[AsyncSession] | None = None


def engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
    return _engine


def fabrica_sesiones() -> async_sessionmaker[AsyncSession]:
    global _fabrica
    if _fabrica is None:
        _fabrica = async_sessionmaker(engine(), expire_on_commit=False)
    return _fabrica


async def get_sesion() -> AsyncIterator[AsyncSession]:
    async with fabrica_sesiones()() as sesion:
        yield sesion


Sesion = Annotated[AsyncSession, Depends(get_sesion)]
