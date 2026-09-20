import uuid
from collections.abc import Sequence

from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.clientes.models import Cliente, MovimientoEnvases, PrecioCliente


def _busqueda(consulta: Select[tuple[Cliente]], texto: str) -> Select[tuple[Cliente]]:
    patron = f"%{texto.strip().lower()}%"
    return consulta.where(
        or_(
            Cliente.nombre_comercial.ilike(patron),
            Cliente.razon_social.ilike(patron),
            Cliente.cuit.ilike(patron),
            Cliente.codigo.ilike(patron),
            Cliente.telefono.ilike(patron),
        )
    )


async def listar(
    sesion: AsyncSession,
    sucursal_id: uuid.UUID | None,
    texto: str | None = None,
    zona_id: uuid.UUID | None = None,
    preventista_id: uuid.UUID | None = None,
    cobrador_id: uuid.UUID | None = None,
    solo_de_preventista: uuid.UUID | None = None,
    solo_de_cobrador: uuid.UUID | None = None,
    incluir_inactivos: bool = False,
    limite: int = 50,
    desde: int = 0,
) -> Sequence[Cliente]:
    consulta = select(Cliente).order_by(Cliente.nombre_comercial).limit(limite).offset(desde)
    if sucursal_id is not None:
        consulta = consulta.where(Cliente.sucursal_id == sucursal_id)
    if not incluir_inactivos:
        consulta = consulta.where(Cliente.activo.is_(True))
    if texto:
        consulta = _busqueda(consulta, texto)
    if zona_id is not None:
        consulta = consulta.where(Cliente.zona_id == zona_id)
    if preventista_id is not None:
        consulta = consulta.where(Cliente.preventista_id == preventista_id)
    if cobrador_id is not None:
        consulta = consulta.where(Cliente.cobrador_id == cobrador_id)
    # Un preventista ve sus clientes y los que todavía no tienen preventista asignado.
    if solo_de_preventista is not None:
        consulta = consulta.where(
            or_(
                Cliente.preventista_id == solo_de_preventista,
                Cliente.preventista_id.is_(None),
            )
        )
    if solo_de_cobrador is not None:
        consulta = consulta.where(Cliente.cobrador_id == solo_de_cobrador)
    return (await sesion.scalars(consulta)).all()


async def por_id(sesion: AsyncSession, cliente_id: uuid.UUID) -> Cliente | None:
    return await sesion.get(Cliente, cliente_id)


async def por_telefono(sesion: AsyncSession, telefono: str) -> Cliente | None:
    return await sesion.scalar(select(Cliente).where(Cliente.telefono == telefono))


async def por_codigo(sesion: AsyncSession, sucursal_id: uuid.UUID, codigo: str) -> Cliente | None:
    return await sesion.scalar(
        select(Cliente).where(Cliente.sucursal_id == sucursal_id, Cliente.codigo == codigo)
    )


async def precios_propios(sesion: AsyncSession, cliente_id: uuid.UUID) -> Sequence[PrecioCliente]:
    return (
        await sesion.scalars(select(PrecioCliente).where(PrecioCliente.cliente_id == cliente_id))
    ).all()


async def precio_propio(
    sesion: AsyncSession, cliente_id: uuid.UUID, producto_id: uuid.UUID
) -> PrecioCliente | None:
    return await sesion.scalar(
        select(PrecioCliente).where(
            PrecioCliente.cliente_id == cliente_id, PrecioCliente.producto_id == producto_id
        )
    )


async def movimientos_envases(
    sesion: AsyncSession, cliente_id: uuid.UUID
) -> Sequence[MovimientoEnvases]:
    consulta = (
        select(MovimientoEnvases)
        .where(MovimientoEnvases.cliente_id == cliente_id)
        .order_by(MovimientoEnvases.fecha)
    )
    return (await sesion.scalars(consulta)).all()
