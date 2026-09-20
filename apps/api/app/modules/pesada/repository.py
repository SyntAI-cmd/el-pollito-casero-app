import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.pesada.models import Cajon


async def por_id(sesion: AsyncSession, cajon_id: uuid.UUID) -> Cajon | None:
    return await sesion.get(Cajon, cajon_id)


async def existentes(sesion: AsyncSession, ids: Sequence[uuid.UUID]) -> Sequence[Cajon]:
    return (await sesion.scalars(select(Cajon).where(Cajon.id.in_(ids)))).all()


async def de_pedido(sesion: AsyncSession, pedido_id: uuid.UUID) -> Sequence[Cajon]:
    consulta = select(Cajon).where(Cajon.pedido_id == pedido_id).order_by(Cajon.pesado_en)
    return (await sesion.scalars(consulta)).all()
