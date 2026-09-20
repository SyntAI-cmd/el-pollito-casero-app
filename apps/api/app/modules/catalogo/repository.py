import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.precios import Lista, Turno
from app.modules.catalogo.models import ListaPrecio, Producto


async def listar_productos(sesion: AsyncSession, solo_activos: bool) -> Sequence[Producto]:
    consulta = select(Producto).order_by(Producto.orden, Producto.nombre)
    if solo_activos:
        consulta = consulta.where(Producto.activo.is_(True))
    return (await sesion.scalars(consulta)).all()


async def producto_por_id(sesion: AsyncSession, producto_id: uuid.UUID) -> Producto | None:
    return await sesion.get(Producto, producto_id)


async def productos_por_codigo(sesion: AsyncSession) -> dict[str, Producto]:
    return {p.codigo: p for p in await listar_productos(sesion, solo_activos=False)}


async def listas_de(
    sesion: AsyncSession,
    sucursal_id: uuid.UUID,
    lista: Lista | None = None,
    turno: Turno | None = None,
) -> Sequence[ListaPrecio]:
    consulta = select(ListaPrecio).where(ListaPrecio.sucursal_id == sucursal_id)
    if lista is not None:
        consulta = consulta.where(ListaPrecio.lista == lista)
    if turno is not None:
        consulta = consulta.where(ListaPrecio.turno == turno)
    return (await sesion.scalars(consulta)).all()


async def fila_de_lista(
    sesion: AsyncSession,
    sucursal_id: uuid.UUID,
    producto_id: uuid.UUID,
    lista: Lista,
    turno: Turno,
    zona_id: uuid.UUID | None,
) -> ListaPrecio | None:
    consulta = select(ListaPrecio).where(
        ListaPrecio.sucursal_id == sucursal_id,
        ListaPrecio.producto_id == producto_id,
        ListaPrecio.lista == lista,
        ListaPrecio.turno == turno,
        ListaPrecio.zona_id.is_(None) if zona_id is None else ListaPrecio.zona_id == zona_id,
    )
    return await sesion.scalar(consulta)
