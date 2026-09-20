import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errores import NoEncontrado
from app.core.seguridad import Identidad
from app.core.tiempo import ahora
from app.domain.errores import ErrorDominio
from app.domain.pedidos import Estado
from app.domain.pesada import Cajon as CajonDominio
from app.domain.pesada import anular_cajon, marcar_cargado, neto, repartir_lote
from app.domain.remitos import formatear_numero
from app.modules.auditoria.service import registrar
from app.modules.catalogo import service as catalogo
from app.modules.pedidos import service as pedidos
from app.modules.pedidos.models import Pedido
from app.modules.pedidos.schemas import PedidoSalida
from app.modules.pesada import repository
from app.modules.pesada.models import Cajon
from app.modules.pesada.schemas import CajonEntrada, CajonSalida, LoteEntrada
from app.modules.sucursales import service as sucursales

# Solo se pesa y se carga antes de que el camión salga.
ABIERTOS = frozenset({Estado.RECIBIDO, Estado.PREPARANDO})


async def _pedido_abierto(sesion: AsyncSession, quien: Identidad, pedido_id: uuid.UUID) -> Pedido:
    pedido = await pedidos.obtener_modelo(sesion, quien, pedido_id)
    if pedido.estado not in ABIERTOS:
        raise ErrorDominio(
            f"El pedido {formatear_numero(pedido.numero)} está {pedido.estado}: no se pesa más"
        )
    return pedido


async def _producto_del_pedido(sesion: AsyncSession, pedido: Pedido, codigo: str) -> uuid.UUID:
    por_codigo = await catalogo.productos_por_codigo(sesion)
    producto = por_codigo.get(codigo)
    if producto is None or producto.id not in {i.producto_id for i in pedido.items}:
        raise ErrorDominio(f"El pedido no tiene {codigo}")
    return producto.id


async def _cerrar(
    sesion: AsyncSession, quien: Identidad, pedido: Pedido, accion: str, detalle: dict[str, object]
) -> PedidoSalida:
    cajones = await repository.de_pedido(sesion, pedido.id)
    await pedidos.recalcular(sesion, quien, pedido, cajones)
    if pedido.estado is Estado.RECIBIDO:
        pedido.estado = Estado.PREPARANDO
    registrar(sesion, quien, accion, "pedido", pedido.id, detalle)
    await sesion.commit()
    return await pedidos.a_salida(sesion, pedido, cajones)


async def pesar_cajon(
    sesion: AsyncSession, quien: Identidad, pedido_id: uuid.UUID, datos: CajonEntrada
) -> PedidoSalida:
    pedido = await _pedido_abierto(sesion, quien, pedido_id)
    existente = await repository.por_id(sesion, datos.id)
    if existente is not None:
        # Reintento offline con la misma id: se responde el estado actual sin duplicar.
        if existente.pedido_id != pedido.id:
            raise ErrorDominio("Esa id de cajón pertenece a otro pedido")
        return await pedidos.a_salida(sesion, pedido)
    sucursal = await sucursales.obtener(sesion, quien, pedido.sucursal_id)
    producto_id = await _producto_del_pedido(sesion, pedido, datos.producto_codigo)
    sesion.add(
        Cajon(
            id=datos.id,
            sucursal_id=pedido.sucursal_id,
            pedido_id=pedido.id,
            producto_id=producto_id,
            bruto=datos.bruto,
            tara=sucursal.tara,
            neto=neto(datos.bruto, sucursal.tara),
            pesado_por=quien.usuario_id,
            pesado_en=datos.pesado_en or ahora(),
        )
    )
    await sesion.flush()
    return await _cerrar(
        sesion,
        quien,
        pedido,
        "pesada.cajon",
        {"cajon_id": str(datos.id), "bruto": str(datos.bruto)},
    )


def ids_de_lote(lote_id: uuid.UUID, cajas: int) -> list[uuid.UUID]:
    """Ids deterministas: el mismo lote reintentado produce los mismos cajones."""
    return [uuid.uuid5(lote_id, str(i)) for i in range(cajas)]


async def pesar_lote(
    sesion: AsyncSession, quien: Identidad, pedido_id: uuid.UUID, datos: LoteEntrada
) -> PedidoSalida:
    pedido = await _pedido_abierto(sesion, quien, pedido_id)
    ids = ids_de_lote(datos.lote_id, datos.cajas)
    ya = await repository.existentes(sesion, ids)
    if ya:
        return await pedidos.a_salida(sesion, pedido)
    sucursal = await sucursales.obtener(sesion, quien, pedido.sucursal_id)
    producto_id = await _producto_del_pedido(sesion, pedido, datos.producto_codigo)
    netos = repartir_lote(datos.cajas, datos.bruto_total, sucursal.tara)
    momento = datos.pesado_en or ahora()
    for cajon_id, neto_cajon in zip(ids, netos, strict=True):
        sesion.add(
            Cajon(
                id=cajon_id,
                sucursal_id=pedido.sucursal_id,
                pedido_id=pedido.id,
                producto_id=producto_id,
                bruto=neto_cajon + sucursal.tara,
                tara=sucursal.tara,
                neto=neto_cajon,
                pesado_por=quien.usuario_id,
                pesado_en=momento,
            )
        )
    await sesion.flush()
    return await _cerrar(
        sesion,
        quien,
        pedido,
        "pesada.lote",
        {
            "lote_id": str(datos.lote_id),
            "cajas": datos.cajas,
            "bruto_total": str(datos.bruto_total),
        },
    )


async def _cajon_con_permiso(
    sesion: AsyncSession, quien: Identidad, cajon_id: uuid.UUID
) -> tuple[Cajon, Pedido]:
    cajon = await repository.por_id(sesion, cajon_id)
    if cajon is None:
        raise NoEncontrado("Cajón")
    pedido = await pedidos.obtener_modelo(sesion, quien, cajon.pedido_id)
    return cajon, pedido


def _a_dominio(cajon: Cajon, codigo: str) -> CajonDominio:
    return CajonDominio(
        str(cajon.id), codigo, cajon.neto, cajon.cargado, cajon.anulado, cajon.motivo_anulacion
    )


async def anular(
    sesion: AsyncSession, quien: Identidad, cajon_id: uuid.UUID, motivo: str
) -> PedidoSalida:
    cajon, pedido = await _cajon_con_permiso(sesion, quien, cajon_id)
    if pedido.estado not in ABIERTOS:
        raise ErrorDominio("El pedido ya salió: el cajón no se anula")
    anulado = anular_cajon(_a_dominio(cajon, ""), motivo)
    cajon.anulado = True
    cajon.motivo_anulacion = anulado.motivo_anulacion
    return await _cerrar(
        sesion, quien, pedido, "pesada.anular", {"cajon_id": str(cajon.id), "motivo": motivo}
    )


async def cargar(
    sesion: AsyncSession, quien: Identidad, cajon_id: uuid.UUID, cargado: bool
) -> PedidoSalida:
    cajon, pedido = await _cajon_con_permiso(sesion, quien, cajon_id)
    if pedido.estado not in ABIERTOS:
        raise ErrorDominio("El pedido ya salió: la carga no se cambia")
    if cargado:
        marcar_cargado(_a_dominio(cajon, ""))
        cajon.cargado = True
        cajon.cargado_en = ahora()
    else:
        cajon.cargado = False
        cajon.cargado_en = None
    cajones = await repository.de_pedido(sesion, pedido.id)
    registrar(
        sesion,
        quien,
        "carga.cajon",
        "pedido",
        pedido.id,
        {"cajon_id": str(cajon.id), "cargado": cargado},
    )
    await sesion.commit()
    return await pedidos.a_salida(sesion, pedido, cajones)


async def cajones_de(
    sesion: AsyncSession, quien: Identidad, pedido_id: uuid.UUID
) -> list[CajonSalida]:
    pedido = await pedidos.obtener_modelo(sesion, quien, pedido_id)
    return await a_salidas(sesion, await repository.de_pedido(sesion, pedido.id))


async def a_salidas(sesion: AsyncSession, cajones: Sequence[Cajon]) -> list[CajonSalida]:
    por_id = {p.id: p.codigo for p in await catalogo.listar_productos(sesion, solo_activos=False)}
    return [
        CajonSalida(
            id=c.id,
            pedido_id=c.pedido_id,
            producto_codigo=por_id[c.producto_id],
            bruto=c.bruto,
            tara=c.tara,
            neto=c.neto,
            cargado=c.cargado,
            cargado_en=c.cargado_en,
            anulado=c.anulado,
            motivo_anulacion=c.motivo_anulacion,
            pesado_en=c.pesado_en,
        )
        for c in cajones
    ]
