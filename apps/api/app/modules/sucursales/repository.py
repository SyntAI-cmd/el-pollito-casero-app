import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sucursales.models import Sucursal, Zona


async def listar_sucursales(sesion: AsyncSession) -> Sequence[Sucursal]:
    return (await sesion.scalars(select(Sucursal).order_by(Sucursal.nombre))).all()


async def sucursal_por_id(sesion: AsyncSession, sucursal_id: uuid.UUID) -> Sucursal | None:
    return await sesion.get(Sucursal, sucursal_id)


async def sucursal_por_nombre(sesion: AsyncSession, nombre: str) -> Sucursal | None:
    return await sesion.scalar(select(Sucursal).where(Sucursal.nombre == nombre))


async def listar_zonas(sesion: AsyncSession, sucursal_id: uuid.UUID) -> Sequence[Zona]:
    consulta = select(Zona).where(Zona.sucursal_id == sucursal_id).order_by(Zona.nombre)
    return (await sesion.scalars(consulta)).all()


async def zona_por_id(sesion: AsyncSession, zona_id: uuid.UUID) -> Zona | None:
    return await sesion.get(Zona, zona_id)


async def zona_por_nombre(sesion: AsyncSession, sucursal_id: uuid.UUID, nombre: str) -> Zona | None:
    return await sesion.scalar(
        select(Zona).where(Zona.sucursal_id == sucursal_id, Zona.nombre == nombre)
    )
