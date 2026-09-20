import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.documentos.models import Documento


async def por_id(sesion: AsyncSession, documento_id: uuid.UUID) -> Documento | None:
    return await sesion.get(Documento, documento_id)


async def del_dia(
    sesion: AsyncSession, fecha: date, creado_por: uuid.UUID | None
) -> Sequence[Documento]:
    consulta = select(Documento).order_by(Documento.creado_en.desc()).limit(200)
    if creado_por is not None:
        consulta = consulta.where(Documento.creado_por == creado_por)
    filas = (await sesion.scalars(consulta)).all()
    return [d for d in filas if d.parametros.get("fecha") == fecha.isoformat()]
