import uuid
from collections.abc import Sequence
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.cobros.models import AjusteCuenta, CierreCaja, Comprobante, Pago


async def pago_por_idempotencia(sesion: AsyncSession, clave: uuid.UUID) -> Pago | None:
    return await sesion.scalar(select(Pago).where(Pago.idempotencia == clave))


async def pago_por_id(sesion: AsyncSession, pago_id: uuid.UUID) -> Pago | None:
    return await sesion.get(Pago, pago_id)


async def pagos_de_cliente(sesion: AsyncSession, cliente_id: uuid.UUID) -> Sequence[Pago]:
    consulta = select(Pago).where(Pago.cliente_id == cliente_id).order_by(Pago.fecha)
    return (await sesion.scalars(consulta)).all()


async def pagos_de_pedido(sesion: AsyncSession, pedido_id: uuid.UUID) -> Sequence[Pago]:
    return (await sesion.scalars(select(Pago).where(Pago.pedido_id == pedido_id))).all()


async def pagos_entre(
    sesion: AsyncSession,
    desde: datetime,
    hasta: datetime,
    cobrado_por: uuid.UUID | None = None,
    sucursal_id: uuid.UUID | None = None,
) -> Sequence[Pago]:
    consulta = select(Pago).where(Pago.fecha >= desde, Pago.fecha < hasta).order_by(Pago.fecha)
    if cobrado_por is not None:
        consulta = consulta.where(Pago.cobrado_por == cobrado_por)
    if sucursal_id is not None:
        consulta = consulta.where(Pago.sucursal_id == sucursal_id)
    return (await sesion.scalars(consulta)).all()


async def ultimo_pago_por_cliente(
    sesion: AsyncSession, cliente_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, datetime]:
    if not cliente_ids:
        return {}
    filas = await sesion.scalars(
        select(Pago).where(Pago.cliente_id.in_(cliente_ids)).order_by(Pago.fecha)
    )
    ultimos: dict[uuid.UUID, datetime] = {}
    for pago in filas:
        ultimos[pago.cliente_id] = pago.fecha
    return ultimos


async def comprobante_por_id(sesion: AsyncSession, comprobante_id: uuid.UUID) -> Comprobante | None:
    return await sesion.get(Comprobante, comprobante_id)


async def comprobantes_de_pedido(
    sesion: AsyncSession, pedido_id: uuid.UUID
) -> Sequence[Comprobante]:
    consulta = (
        select(Comprobante)
        .where(Comprobante.pedido_id == pedido_id)
        .order_by(Comprobante.creado_en)
    )
    return (await sesion.scalars(consulta)).all()


async def comprobantes_entre(
    sesion: AsyncSession,
    desde: datetime,
    hasta: datetime,
    subido_por: uuid.UUID | None,
    sucursal_id: uuid.UUID | None,
) -> Sequence[Comprobante]:
    consulta = (
        select(Comprobante)
        .where(Comprobante.creado_en >= desde, Comprobante.creado_en < hasta)
        .order_by(Comprobante.creado_en)
    )
    if subido_por is not None:
        consulta = consulta.where(Comprobante.subido_por == subido_por)
    if sucursal_id is not None:
        consulta = consulta.where(Comprobante.sucursal_id == sucursal_id)
    return (await sesion.scalars(consulta)).all()


async def ajustes_de_cliente(sesion: AsyncSession, cliente_id: uuid.UUID) -> Sequence[AjusteCuenta]:
    consulta = (
        select(AjusteCuenta)
        .where(AjusteCuenta.cliente_id == cliente_id)
        .order_by(AjusteCuenta.fecha)
    )
    return (await sesion.scalars(consulta)).all()


async def cierre_de(sesion: AsyncSession, usuario_id: uuid.UUID, fecha: date) -> CierreCaja | None:
    return await sesion.scalar(
        select(CierreCaja).where(CierreCaja.usuario_id == usuario_id, CierreCaja.fecha == fecha)
    )


async def cierres_del_dia(
    sesion: AsyncSession, fecha: date, sucursal_id: uuid.UUID | None
) -> Sequence[CierreCaja]:
    consulta = select(CierreCaja).where(CierreCaja.fecha == fecha)
    if sucursal_id is not None:
        consulta = consulta.where(CierreCaja.sucursal_id == sucursal_id)
    return (await sesion.scalars(consulta)).all()
