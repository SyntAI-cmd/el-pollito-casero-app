import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import SesionRefresh, TokenPush, Usuario


async def por_usuario(sesion: AsyncSession, usuario: str) -> Usuario | None:
    return await sesion.scalar(select(Usuario).where(Usuario.usuario == usuario))


async def por_id(sesion: AsyncSession, usuario_id: uuid.UUID) -> Usuario | None:
    return await sesion.get(Usuario, usuario_id)


async def listar(sesion: AsyncSession, sucursal_id: uuid.UUID | None) -> Sequence[Usuario]:
    consulta = select(Usuario).order_by(Usuario.nombre)
    if sucursal_id is not None:
        consulta = consulta.where(Usuario.sucursal_id == sucursal_id)
    return (await sesion.scalars(consulta)).all()


async def sesion_refresh(sesion: AsyncSession, jti: uuid.UUID) -> SesionRefresh | None:
    return await sesion.get(SesionRefresh, jti)


async def token_push(sesion: AsyncSession, token: str) -> TokenPush | None:
    return await sesion.scalar(select(TokenPush).where(TokenPush.token == token))


async def tokens_push_de(sesion: AsyncSession, usuario_ids: Sequence[uuid.UUID]) -> list[str]:
    if not usuario_ids:
        return []
    filas = await sesion.scalars(
        select(TokenPush.token).where(TokenPush.usuario_id.in_(usuario_ids))
    )
    return list(filas)
