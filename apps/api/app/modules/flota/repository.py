import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.flota.models import Salida, SalidaTrack, Vehiculo


async def listar_vehiculos(
    sesion: AsyncSession, sucursal_id: uuid.UUID | None, incluir_inactivos: bool
) -> Sequence[Vehiculo]:
    consulta = select(Vehiculo).order_by(Vehiculo.nombre, Vehiculo.patente)
    if sucursal_id is not None:
        consulta = consulta.where(Vehiculo.sucursal_id == sucursal_id)
    if not incluir_inactivos:
        consulta = consulta.where(Vehiculo.activo.is_(True))
    return (await sesion.scalars(consulta)).all()


async def vehiculo_por_id(sesion: AsyncSession, vehiculo_id: uuid.UUID) -> Vehiculo | None:
    return await sesion.get(Vehiculo, vehiculo_id)


async def vehiculo_por_patente(sesion: AsyncSession, patente: str) -> Vehiculo | None:
    return await sesion.scalar(select(Vehiculo).where(Vehiculo.patente == patente))


async def salidas_del_dia(
    sesion: AsyncSession, sucursal_id: uuid.UUID | None, fecha: date
) -> Sequence[Salida]:
    consulta = select(Salida).where(Salida.fecha == fecha).order_by(Salida.hora_salida)
    if sucursal_id is not None:
        consulta = consulta.where(Salida.sucursal_id == sucursal_id)
    return (await sesion.scalars(consulta)).all()


async def salida_por_id(sesion: AsyncSession, salida_id: uuid.UUID) -> Salida | None:
    return await sesion.get(Salida, salida_id)


async def salida_de_vehiculo(
    sesion: AsyncSession, vehiculo_id: uuid.UUID, fecha: date
) -> Salida | None:
    return await sesion.scalar(
        select(Salida).where(Salida.vehiculo_id == vehiculo_id, Salida.fecha == fecha)
    )


async def salida_de_preventista(
    sesion: AsyncSession, preventista_id: uuid.UUID, fecha: date
) -> Salida | None:
    return await sesion.scalar(
        select(Salida).where(
            Salida.fecha == fecha,
            or_(
                Salida.preventista_id == preventista_id,
                Salida.segundo_preventista_id == preventista_id,
            ),
        )
    )


async def ultima_posicion(sesion: AsyncSession, salida_id: uuid.UUID) -> SalidaTrack | None:
    consulta = (
        select(SalidaTrack)
        .where(SalidaTrack.salida_id == salida_id)
        .order_by(SalidaTrack.registrado_en.desc())
        .limit(1)
    )
    return await sesion.scalar(consulta)


async def recorrido(
    sesion: AsyncSession, salida_id: uuid.UUID, limite: int = 600
) -> Sequence[SalidaTrack]:
    consulta = (
        select(SalidaTrack)
        .where(SalidaTrack.salida_id == salida_id)
        .order_by(SalidaTrack.registrado_en.desc())
        .limit(limite)
    )
    return list(reversed((await sesion.scalars(consulta)).all()))
