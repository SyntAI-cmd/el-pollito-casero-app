import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.comunicacion.models import Mensaje, Noticia


async def noticias(
    sesion: AsyncSession, sucursal_id: uuid.UUID, incluir_archivadas: bool
) -> Sequence[Noticia]:
    consulta = (
        select(Noticia)
        .where(Noticia.sucursal_id == sucursal_id)
        .order_by(Noticia.fijada.desc(), Noticia.creado_en.desc())
        .limit(100)
    )
    if not incluir_archivadas:
        consulta = consulta.where(Noticia.archivada.is_(False))
    return (await sesion.scalars(consulta)).all()


async def noticia_por_id(sesion: AsyncSession, noticia_id: uuid.UUID) -> Noticia | None:
    return await sesion.get(Noticia, noticia_id)


async def mensajes(sesion: AsyncSession, sucursal_id: uuid.UUID, limite: int) -> Sequence[Mensaje]:
    consulta = (
        select(Mensaje)
        .where(Mensaje.sucursal_id == sucursal_id)
        .order_by(Mensaje.creado_en.desc())
        .limit(limite)
    )
    return list(reversed((await sesion.scalars(consulta)).all()))
