import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.pedidos import Estado
from app.domain.precios import Turno
from app.domain.remitos import siguiente_numero
from app.modules.pedidos.models import Contador, Pedido, PedidoEvento
from app.modules.pesada.models import Cajon

NOMBRE_CONTADOR_REMITOS = "remito"


async def tomar_numero_remito(sesion: AsyncSession) -> int:
    """Lee el contador con FOR UPDATE: la transacción del pedido lo bloquea hasta el commit."""
    contador = await sesion.scalar(
        select(Contador).where(Contador.nombre == NOMBRE_CONTADOR_REMITOS).with_for_update()
    )
    if contador is None:
        contador = Contador(nombre=NOMBRE_CONTADOR_REMITOS, valor=0)
        sesion.add(contador)
        await sesion.flush()
    contador.valor = siguiente_numero(contador.valor)
    return contador.valor


def _con_items(consulta: Select[tuple[Pedido]]) -> Select[tuple[Pedido]]:
    return consulta.options(selectinload(Pedido.items))


async def por_id(sesion: AsyncSession, pedido_id: uuid.UUID) -> Pedido | None:
    return await sesion.scalar(_con_items(select(Pedido).where(Pedido.id == pedido_id)))


async def listar(
    sesion: AsyncSession,
    sucursal_id: uuid.UUID | None,
    fecha: date | None = None,
    turno: Turno | None = None,
    estado: Estado | None = None,
    cliente_id: uuid.UUID | None = None,
    preventista_id: uuid.UUID | None = None,
    solo_de_preventista: uuid.UUID | None = None,
    salida_id: uuid.UUID | None = None,
    limite: int = 200,
    desde: int = 0,
) -> Sequence[Pedido]:
    consulta = _con_items(select(Pedido).order_by(Pedido.numero.desc()).limit(limite).offset(desde))
    if sucursal_id is not None:
        consulta = consulta.where(Pedido.sucursal_id == sucursal_id)
    if fecha is not None:
        consulta = consulta.where(Pedido.fecha_reparto == fecha)
    if turno is not None:
        consulta = consulta.where(Pedido.turno == turno)
    if estado is not None:
        consulta = consulta.where(Pedido.estado == estado)
    if cliente_id is not None:
        consulta = consulta.where(Pedido.cliente_id == cliente_id)
    if preventista_id is not None:
        consulta = consulta.where(
            or_(
                Pedido.preventista_id == preventista_id,
                Pedido.segundo_preventista_id == preventista_id,
            )
        )
    if solo_de_preventista is not None:
        consulta = consulta.where(
            or_(
                Pedido.preventista_id == solo_de_preventista,
                Pedido.segundo_preventista_id == solo_de_preventista,
            )
        )
    if salida_id is not None:
        consulta = consulta.where(Pedido.salida_id == salida_id)
    return (await sesion.scalars(consulta)).all()


async def cajones_de(sesion: AsyncSession, pedido_id: uuid.UUID) -> Sequence[Cajon]:
    consulta = select(Cajon).where(Cajon.pedido_id == pedido_id).order_by(Cajon.pesado_en)
    return (await sesion.scalars(consulta)).all()


async def cajones_de_varios(
    sesion: AsyncSession, pedido_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, list[Cajon]]:
    if not pedido_ids:
        return {}
    filas = await sesion.scalars(select(Cajon).where(Cajon.pedido_id.in_(pedido_ids)))
    agrupados: dict[uuid.UUID, list[Cajon]] = {pid: [] for pid in pedido_ids}
    for cajon in filas:
        agrupados[cajon.pedido_id].append(cajon)
    return agrupados


async def eventos_de(sesion: AsyncSession, pedido_id: uuid.UUID) -> Sequence[PedidoEvento]:
    consulta = (
        select(PedidoEvento)
        .where(PedidoEvento.pedido_id == pedido_id)
        .order_by(PedidoEvento.creado_en)
    )
    return (await sesion.scalars(consulta)).all()
