import uuid
from collections import defaultdict
from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from types import ModuleType
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errores import Conflicto, NoEncontrado, SinPermiso
from app.core.seguridad import Identidad, Rol
from app.core.tiempo import ahora
from app.core.tiempo_real import difusor
from app.domain.dinero import CERO, a_kilos
from app.domain.errores import ErrorDominio
from app.domain.pedidos import Estado, PedidoParaCargar, transicionar
from app.domain.pesada import Cajon as CajonDominio
from app.domain.pesada import kilos_por_producto
from app.domain.precios import (
    Renglon,
    Totales,
    Turno,
    resolver_precio,
    totales_pedido,
    validar_precio,
)
from app.domain.remitos import formatear_numero
from app.integrations.push import Notificacion, enviador_push
from app.modules.auditoria.service import registrar
from app.modules.auth import service as auth
from app.modules.catalogo import service as catalogo
from app.modules.catalogo.models import Producto
from app.modules.clientes import service as clientes
from app.modules.clientes.schemas import PrecioPropioEntrada, PreciosPropiosEntrada
from app.modules.pedidos import repository
from app.modules.pedidos.models import Pedido, PedidoEvento, PedidoItem
from app.modules.pedidos.schemas import (
    EstadoEntrada,
    GrupoPreventista,
    ItemSalida,
    NotaDelDia,
    PedidoCambios,
    PedidoEntrada,
    PedidoSalida,
    PreciosPedidoEntrada,
    TotalProducto,
)
from app.modules.pesada.models import Cajon
from app.modules.sucursales.service import verificar_sucursal

# ---------- permisos ----------


def puede_ver(quien: Identidad, pedido: Pedido) -> bool:
    if quien.rol is Rol.ADMIN:
        return True
    if pedido.sucursal_id != quien.sucursal_id:
        return False
    if quien.rol is Rol.PREVENTISTA:
        return quien.usuario_id in (pedido.preventista_id, pedido.segundo_preventista_id)
    return False


async def obtener_modelo(sesion: AsyncSession, quien: Identidad, pedido_id: uuid.UUID) -> Pedido:
    pedido = await repository.por_id(sesion, pedido_id)
    if pedido is None or not puede_ver(quien, pedido):
        raise NoEncontrado("Pedido")
    return pedido


def _verificar_abierto(pedido: Pedido) -> None:
    if pedido.estado in (Estado.ENTREGADO, Estado.CANCELADO):
        raise Conflicto(f"El pedido {formatear_numero(pedido.numero)} ya está {pedido.estado}")


# ---------- cálculo ----------


def _renglones(
    pedido: Pedido, cajones: Sequence[Cajon], por_id: dict[uuid.UUID, Producto]
) -> list[Renglon]:
    pesados = kilos_por_producto(
        [
            CajonDominio(str(c.id), por_id[c.producto_id].codigo, c.neto, c.cargado, c.anulado)
            for c in cajones
        ]
    )
    return [
        Renglon(
            producto_id=por_id[item.producto_id].codigo,
            precio=item.precio,
            cajas=item.cajas,
            kg_pedidos=item.kg_pedidos,
            kg_pesados=pesados.get(por_id[item.producto_id].codigo),
        )
        for item in pedido.items
    ]


async def recalcular(
    sesion: AsyncSession, quien: Identidad, pedido: Pedido, cajones: Sequence[Cajon]
) -> Totales:
    """
    Reescribe kilos pesados, importes y totales a partir de los cajones. Si el pedido ya estaba
    pagado y el total cambió (repesada, precio corregido), la diferencia va al saldo a favor del
    cliente: lo cobrado no se toca, se compensa en el próximo pedido.
    """
    por_id = {p.id: p for p in await catalogo.listar_productos(sesion, solo_activos=False)}
    renglones = _renglones(pedido, cajones, por_id)
    totales = totales_pedido(renglones)
    for item, renglon in zip(pedido.items, renglones, strict=True):
        item.kg_pesados = renglon.kg_pesados
        item.importe = renglon.importe
    total_anterior = pedido.total
    pedido.subtotal = totales.subtotal
    # `estimado` queda como se cargó: es el cargo original del extracto; la balanza agrega el resto.
    pedido.total = totales.subtotal
    if not totales.sin_pesar and pedido.pesado_en is None:
        pedido.pesado_en = ahora()
    if totales.sin_pesar:
        pedido.pesado_en = None
    if pedido.pagado and pedido.total != total_anterior:
        # Ya cobrado por otro importe: la diferencia va a la cuenta (a favor si pagó de más).
        await _cobros().registrar_ajuste(
            sesion,
            quien,
            pedido.cliente_id,
            _cobros().TipoAjuste.REPESADA,
            pedido.total - total_anterior,
            f"Pedido {formatear_numero(pedido.numero)} recalculado después de pagado",
            referencia=formatear_numero(pedido.numero),
        )
    return totales


def _cobros() -> ModuleType:
    """cobros importa pedidos; se importa acá adentro para no cerrar el círculo al cargar."""
    from app.modules.cobros import service as cobros

    return cobros


def _evento(
    sesion: AsyncSession, pedido: Pedido, tipo: str, quien: Identidad, **detalle: Any
) -> None:
    sesion.add(
        PedidoEvento(
            pedido_id=pedido.id,
            tipo=tipo,
            detalle=detalle,
            usuario_id=quien.usuario_id,
            creado_en=ahora(),
        )
    )


async def _publicar(pedido: Pedido, tipo: str) -> None:
    datos = {
        "pedido_id": str(pedido.id),
        "numero": formatear_numero(pedido.numero),
        "estado": pedido.estado,
    }
    await difusor.publicar(pedido.sucursal_id, tipo, datos, roles=frozenset({Rol.ADMIN}))
    asignados = {u for u in (pedido.preventista_id, pedido.segundo_preventista_id) if u}
    if asignados:
        await difusor.publicar(
            pedido.sucursal_id,
            tipo,
            datos,
            roles=frozenset({Rol.PREVENTISTA}),
            solo_usuarios=asignados,
        )


# ---------- salida ----------


async def a_salida(
    sesion: AsyncSession,
    pedido: Pedido,
    cajones: Sequence[Cajon] | None = None,
    por_id: dict[uuid.UUID, Producto] | None = None,
) -> PedidoSalida:
    if cajones is None:
        cajones = await repository.cajones_de(sesion, pedido.id)
    if por_id is None:
        por_id = {p.id: p for p in await catalogo.listar_productos(sesion, solo_activos=False)}
    cliente = await clientes.obtener_interno(sesion, pedido.cliente_id)
    vivos = [c for c in cajones if not c.anulado]
    renglones = _renglones(pedido, cajones, por_id)
    totales = totales_pedido(renglones)
    items = [
        ItemSalida(
            producto_codigo=por_id[item.producto_id].codigo,
            producto_nombre=por_id[item.producto_id].nombre,
            cajas=item.cajas,
            kg_pedidos=item.kg_pedidos,
            kg_pesados=item.kg_pesados,
            precio=item.precio,
            precio_propio=item.precio_propio,
            importe=item.importe,
            cajones=sum(1 for c in vivos if c.producto_id == item.producto_id),
            cajones_cargados=sum(
                1 for c in vivos if c.producto_id == item.producto_id and c.cargado
            ),
        )
        for item in pedido.items
    ]
    return PedidoSalida(
        id=pedido.id,
        numero=formatear_numero(pedido.numero),
        sucursal_id=pedido.sucursal_id,
        cliente_id=pedido.cliente_id,
        cliente_nombre=cliente.nombre_comercial,
        cliente_direccion=cliente.direccion,
        cliente_telefono=cliente.telefono,
        cliente_lat=cliente.lat,
        cliente_lng=cliente.lng,
        estado=pedido.estado,
        turno=pedido.turno,
        fecha_reparto=pedido.fecha_reparto,
        a_cuenta=pedido.a_cuenta,
        pagado=pedido.pagado,
        subtotal=pedido.subtotal,
        estimado=pedido.estimado,
        total=pedido.total,
        preventista_id=pedido.preventista_id,
        segundo_preventista_id=pedido.segundo_preventista_id,
        vehiculo_id=pedido.vehiculo_id,
        salida_id=pedido.salida_id,
        zona_id=pedido.zona_id,
        observaciones=pedido.observaciones,
        items=items,
        sin_precio=list(totales.sin_precio),
        sin_pesar=list(totales.sin_pesar),
        cajones=len(vivos),
        cajones_cargados=sum(1 for c in vivos if c.cargado),
        creado_en=pedido.creado_en,
        pesado_en=pedido.pesado_en,
        entregado_en=pedido.entregado_en,
        cancelado_en=pedido.cancelado_en,
        motivo_cancelacion=pedido.motivo_cancelacion,
    )


async def a_salidas(sesion: AsyncSession, pedidos: Sequence[Pedido]) -> list[PedidoSalida]:
    por_id = {p.id: p for p in await catalogo.listar_productos(sesion, solo_activos=False)}
    cajones = await repository.cajones_de_varios(sesion, [p.id for p in pedidos])
    return [await a_salida(sesion, p, cajones[p.id], por_id) for p in pedidos]


# ---------- operaciones ----------


async def _precios_del_cliente(
    sesion: AsyncSession, cliente_id: uuid.UUID
) -> tuple[dict[str, Decimal], Any, Any]:
    cliente = await clientes.obtener_interno(sesion, cliente_id)
    propios = await clientes.precios_propios_como_mapa(sesion, cliente.id)
    listas = await catalogo.listas_como_dominio(
        sesion, cliente.sucursal_id, cliente.lista, cliente.turno
    )
    return propios, listas, cliente


async def crear(sesion: AsyncSession, quien: Identidad, datos: PedidoEntrada) -> PedidoSalida:
    cliente = await clientes.obtener(sesion, quien, datos.cliente_id)
    verificar_sucursal(quien, cliente.sucursal_id)
    if datos.a_cuenta and not cliente.credito_habilitado:
        raise ErrorDominio(f"{cliente.nombre_comercial} no tiene cuenta corriente habilitada")
    preventista_id = datos.preventista_id
    if quien.rol is Rol.PREVENTISTA:
        if preventista_id not in (None, quien.usuario_id):
            raise SinPermiso("Un preventista carga pedidos a su nombre")
        preventista_id = quien.usuario_id
    if preventista_id and preventista_id == datos.segundo_preventista_id:
        raise ErrorDominio("El segundo preventista tiene que ser otra persona")

    por_codigo = await catalogo.productos_por_codigo(sesion)
    propios, listas, _ = await _precios_del_cliente(sesion, cliente.id)
    zona = str(cliente.zona_id) if cliente.zona_id else None
    items: list[PedidoItem] = []
    renglones: list[Renglon] = []
    a_guardar: list[PrecioPropioEntrada] = []
    for orden, entrada in enumerate(datos.items):
        producto = por_codigo.get(entrada.producto_codigo)
        if producto is None or not producto.activo:
            raise ErrorDominio(f"Producto desconocido: {entrada.producto_codigo}")
        if entrada.precio is not None:
            precio: Decimal | None = validar_precio(entrada.precio)
            if entrada.guardar_precio_propio:
                a_guardar.append(
                    PrecioPropioEntrada(producto_codigo=producto.codigo, precio=precio)
                )
        else:
            precio = resolver_precio(
                producto.codigo, propios, listas, cliente.lista, cliente.turno, zona
            )
        renglones.append(
            Renglon(
                producto_id=producto.codigo,
                precio=precio,
                cajas=entrada.cajas,
                kg_pedidos=a_kilos(entrada.kg) if entrada.kg is not None else None,
            )
        )
        items.append(
            PedidoItem(
                producto_id=producto.id,
                orden=orden,
                cajas=entrada.cajas,
                kg_pedidos=a_kilos(entrada.kg) if entrada.kg is not None else None,
                precio=precio,
                precio_propio=entrada.precio is not None or producto.codigo in propios,
                importe=CERO,
            )
        )
    totales = totales_pedido(renglones)

    numero = await repository.tomar_numero_remito(sesion)
    pedido = Pedido(
        numero=numero,
        sucursal_id=cliente.sucursal_id,
        cliente_id=cliente.id,
        preventista_id=preventista_id,
        segundo_preventista_id=datos.segundo_preventista_id,
        vehiculo_id=datos.vehiculo_id,
        zona_id=datos.zona_id or cliente.zona_id,
        turno=datos.turno,
        fecha_reparto=datos.fecha_reparto,
        estado=Estado.RECIBIDO,
        a_cuenta=datos.a_cuenta,
        subtotal=totales.subtotal,
        estimado=totales.estimado,
        total=totales.subtotal,
        observaciones=datos.observaciones.strip(),
        creado_por=quien.usuario_id,
        items=items,
    )
    sesion.add(pedido)
    await sesion.flush()
    if a_guardar:
        await clientes.guardar_precios_propios(
            sesion, quien, cliente.id, PreciosPropiosEntrada(precios=a_guardar), commit=False
        )
    _evento(sesion, pedido, "creado", quien, estimado=str(totales.estimado))
    registrar(
        sesion,
        quien,
        "pedido.crear",
        "pedido",
        pedido.id,
        {"numero": formatear_numero(numero), "cliente_id": str(cliente.id)},
    )
    await sesion.commit()
    await sesion.refresh(pedido, attribute_names=["items", "creado_en"])
    await _publicar(pedido, "pedido.creado")
    await _avisar_asignacion(sesion, quien, pedido, cliente.nombre_comercial)
    return await a_salida(sesion, pedido, [])


async def _avisar_asignacion(
    sesion: AsyncSession, quien: Identidad, pedido: Pedido, cliente_nombre: str
) -> None:
    """Push al preventista cuando otro (administración) le carga un pedido."""
    destinatarios = [
        u
        for u in (pedido.preventista_id, pedido.segundo_preventista_id)
        if u and u != quien.usuario_id
    ]
    if not destinatarios:
        return
    tokens = await auth.tokens_push_de(sesion, destinatarios)
    await enviador_push().enviar(
        tokens,
        Notificacion(
            titulo=f"Pedido #{formatear_numero(pedido.numero)}",
            cuerpo=f"{cliente_nombre} · {pedido.fecha_reparto:%d/%m} {pedido.turno}",
            datos={"pedido_id": str(pedido.id)},
        ),
    )


async def listar(
    sesion: AsyncSession,
    quien: Identidad,
    fecha: date | None,
    turno: Turno | None,
    estado: Estado | None,
    cliente_id: uuid.UUID | None,
    preventista_id: uuid.UUID | None,
    limite: int,
    desde: int,
) -> list[PedidoSalida]:
    if quien.rol is Rol.COBRADOR:
        raise SinPermiso("El cobrador no ve pedidos")
    pedidos = await repository.listar(
        sesion,
        sucursal_id=None if quien.rol is Rol.ADMIN else quien.sucursal_id,
        fecha=fecha,
        turno=turno,
        estado=estado,
        cliente_id=cliente_id,
        preventista_id=preventista_id,
        solo_de_preventista=quien.usuario_id if quien.rol is Rol.PREVENTISTA else None,
        limite=limite,
        desde=desde,
    )
    return await a_salidas(sesion, pedidos)


async def obtener(sesion: AsyncSession, quien: Identidad, pedido_id: uuid.UUID) -> PedidoSalida:
    return await a_salida(sesion, await obtener_modelo(sesion, quien, pedido_id))


async def modificar(
    sesion: AsyncSession, quien: Identidad, pedido_id: uuid.UUID, cambios: PedidoCambios
) -> PedidoSalida:
    pedido = await obtener_modelo(sesion, quien, pedido_id)
    _verificar_abierto(pedido)
    datos = cambios.model_dump(exclude_unset=True)
    if quien.rol is Rol.PREVENTISTA and "preventista_id" in datos:
        raise SinPermiso("Solo administración reasigna pedidos")
    if "a_cuenta" in datos and datos["a_cuenta"]:
        cliente = await clientes.obtener_interno(sesion, pedido.cliente_id)
        if not cliente.credito_habilitado:
            raise ErrorDominio(f"{cliente.nombre_comercial} no tiene cuenta corriente habilitada")
    for campo, valor in datos.items():
        setattr(pedido, campo, valor.strip() if isinstance(valor, str) else valor)
    if pedido.preventista_id and pedido.preventista_id == pedido.segundo_preventista_id:
        raise ErrorDominio("El segundo preventista tiene que ser otra persona")
    _evento(sesion, pedido, "modificado", quien, campos=sorted(datos))
    registrar(sesion, quien, "pedido.modificar", "pedido", pedido.id, {"campos": sorted(datos)})
    await sesion.commit()
    await _publicar(pedido, "pedido.actualizado")
    return await a_salida(sesion, pedido)


async def cambiar_precios(
    sesion: AsyncSession, quien: Identidad, pedido_id: uuid.UUID, datos: PreciosPedidoEntrada
) -> PedidoSalida:
    """Cualquiera del equipo con acceso al pedido corrige el precio por kilo de un renglón."""
    pedido = await obtener_modelo(sesion, quien, pedido_id)
    _verificar_abierto(pedido)
    por_codigo = await catalogo.productos_por_codigo(sesion)
    por_item = {item.producto_id: item for item in pedido.items}
    a_guardar: list[PrecioPropioEntrada] = []
    cambios: dict[str, str] = {}
    for entrada in datos.precios:
        producto = por_codigo.get(entrada.producto_codigo)
        if producto is None or producto.id not in por_item:
            raise ErrorDominio(f"El pedido no tiene {entrada.producto_codigo}")
        precio = validar_precio(entrada.precio)
        por_item[producto.id].precio = precio
        por_item[producto.id].precio_propio = True
        cambios[producto.codigo] = str(precio)
        if entrada.guardar_precio_propio:
            a_guardar.append(PrecioPropioEntrada(producto_codigo=producto.codigo, precio=precio))
    cajones = await repository.cajones_de(sesion, pedido.id)
    await recalcular(sesion, quien, pedido, cajones)
    if a_guardar:
        await clientes.guardar_precios_propios(
            sesion, quien, pedido.cliente_id, PreciosPropiosEntrada(precios=a_guardar), commit=False
        )
    _evento(sesion, pedido, "precios", quien, precios=cambios, total=str(pedido.total))
    registrar(sesion, quien, "pedido.precios", "pedido", pedido.id, {"precios": cambios})
    await sesion.commit()
    await _publicar(pedido, "pedido.actualizado")
    return await a_salida(sesion, pedido, cajones)


async def cambiar_estado(
    sesion: AsyncSession, quien: Identidad, pedido_id: uuid.UUID, datos: EstadoEntrada
) -> PedidoSalida:
    pedido = await obtener_modelo(sesion, quien, pedido_id)
    anterior = pedido.estado
    pedido.estado = transicionar(anterior, datos.estado)
    momento = ahora()
    if datos.estado is Estado.ENTREGADO:
        await _cobros().verificar_cierre_entrega(sesion, pedido.id)
        pedido.entregado_en = momento
    if datos.estado is Estado.CANCELADO:
        if not (datos.motivo and datos.motivo.strip()):
            raise ErrorDominio("Indicá el motivo de la cancelación")
        pedido.cancelado_en = momento
        pedido.motivo_cancelacion = datos.motivo.strip()
    _evento(sesion, pedido, "estado", quien, de=anterior, a=datos.estado, motivo=datos.motivo)
    registrar(
        sesion, quien, "pedido.estado", "pedido", pedido.id, {"de": anterior, "a": datos.estado}
    )
    await sesion.commit()
    await _publicar(pedido, "pedido.estado")
    return await a_salida(sesion, pedido)


async def eliminar(sesion: AsyncSession, quien: Identidad, pedido_id: uuid.UUID) -> None:
    """
    Borra el pedido con sus cajones. Queda la foto completa en audit_log y, si ya estaba pagado,
    lo cobrado vuelve como saldo a favor del cliente (no se devuelve plata en mano).
    """
    if quien.rol is not Rol.ADMIN:
        raise SinPermiso("Solo administración borra pedidos")
    pedido = await obtener_modelo(sesion, quien, pedido_id)
    salida = await a_salida(sesion, pedido)
    if pedido.pagado and pedido.total > CERO:
        await _cobros().registrar_ajuste(
            sesion,
            quien,
            pedido.cliente_id,
            _cobros().TipoAjuste.REINTEGRO,
            -pedido.total,
            f"Reintegro por pedido {salida.numero} borrado",
            referencia=salida.numero,
        )
    registrar(
        sesion,
        quien,
        "pedido.eliminar",
        "pedido",
        pedido.id,
        {"pedido": salida.model_dump(mode="json")},
    )
    await sesion.delete(pedido)
    await sesion.commit()
    await difusor.publicar(
        pedido.sucursal_id,
        "pedido.eliminado",
        {"pedido_id": str(pedido.id), "numero": salida.numero},
    )


async def eventos(
    sesion: AsyncSession, quien: Identidad, pedido_id: uuid.UUID
) -> list[PedidoEvento]:
    pedido = await obtener_modelo(sesion, quien, pedido_id)
    return list(await repository.eventos_de(sesion, pedido.id))


async def nota_del_dia(
    sesion: AsyncSession, quien: Identidad, fecha: date, turno: Turno | None
) -> NotaDelDia:
    """La hoja amarilla hecha datos: totales por producto y pedidos por preventista."""
    if quien.rol is Rol.COBRADOR:
        raise SinPermiso("El cobrador no ve la nota del día")
    pedidos = await repository.listar(
        sesion,
        sucursal_id=None if quien.rol is Rol.ADMIN else quien.sucursal_id,
        fecha=fecha,
        turno=turno,
        solo_de_preventista=quien.usuario_id if quien.rol is Rol.PREVENTISTA else None,
        limite=2000,
    )
    pedidos = [p for p in pedidos if p.estado is not Estado.CANCELADO]
    salidas = await a_salidas(sesion, pedidos)
    por_producto: dict[str, TotalProducto] = {}
    for salida in salidas:
        for item in salida.items:
            acumulado = por_producto.setdefault(
                item.producto_codigo,
                TotalProducto(
                    producto_codigo=item.producto_codigo,
                    producto_nombre=item.producto_nombre,
                    cajas=0,
                    kg_pedidos=CERO,
                    kg_pesados=CERO,
                    pedidos=0,
                ),
            )
            acumulado.cajas += item.cajas or 0
            acumulado.kg_pedidos += item.kg_pedidos or CERO
            acumulado.kg_pesados += item.kg_pesados or CERO
            acumulado.pedidos += 1
    grupos: dict[uuid.UUID | None, list[PedidoSalida]] = defaultdict(list)
    for salida in salidas:
        grupos[salida.preventista_id].append(salida)
    nombres = {u.id: u.nombre for u in await _usuarios(sesion)}
    por_preventista = [
        GrupoPreventista(
            preventista_id=pid,
            preventista_nombre=nombres.get(pid, "Sin asignar") if pid else "Sin asignar",
            pedidos=lista,
            cajones=sum(p.cajones for p in lista),
            kilos=sum((i.kg_pesados or CERO for p in lista for i in p.items), CERO),
            importe=sum((p.total for p in lista), CERO),
        )
        for pid, lista in sorted(
            grupos.items(), key=lambda g: nombres.get(g[0] or uuid.UUID(int=0), "~")
        )
    ]
    return NotaDelDia(
        fecha=fecha,
        turno=turno,
        cantidad_pedidos=len(salidas),
        cajones=sum(p.cajones for p in salidas),
        kilos=sum((i.kg_pesados or CERO for p in salidas for i in p.items), CERO),
        importe=sum((p.total for p in salidas), CERO),
        por_producto=sorted(por_producto.values(), key=lambda t: t.producto_codigo),
        por_preventista=por_preventista,
    )


async def _usuarios(sesion: AsyncSession) -> Sequence[Any]:
    return await auth.listar_todos(sesion)


# ---------- para flota ----------


async def modelos_para_salida(
    sesion: AsyncSession, sucursal_id: uuid.UUID, fecha: date, preventistas: set[uuid.UUID]
) -> list[Pedido]:
    """Pedidos vivos del día que van en un camión: los de sus preventistas, sin cancelados."""
    pedidos = await repository.listar(sesion, sucursal_id=sucursal_id, fecha=fecha, limite=2000)
    return [
        p
        for p in pedidos
        if p.estado not in (Estado.CANCELADO, Estado.ENTREGADO)
        and (p.preventista_id in preventistas or p.segundo_preventista_id in preventistas)
    ]


async def para_cargar(sesion: AsyncSession, pedidos: Sequence[Pedido]) -> list[PedidoParaCargar]:
    por_id = {p.id: p for p in await catalogo.listar_productos(sesion, solo_activos=False)}
    cajones = await repository.cajones_de_varios(sesion, [p.id for p in pedidos])
    return [
        PedidoParaCargar(
            id=str(p.id),
            numero=formatear_numero(p.numero),
            cajas_pedidas=sum(i.cajas or 0 for i in p.items),
            cajones=[
                CajonDominio(str(c.id), por_id[c.producto_id].codigo, c.neto, c.cargado, c.anulado)
                for c in cajones[p.id]
            ],
        )
        for p in pedidos
    ]


async def despachar(
    sesion: AsyncSession, quien: Identidad, pedidos: Sequence[Pedido], salida_id: uuid.UUID
) -> None:
    """Cerrar camión: los pedidos pasan a en_camino y quedan atados a la salida. No commitea."""
    for pedido in pedidos:
        if pedido.estado is Estado.EN_CAMINO:
            continue
        anterior = pedido.estado
        pedido.estado = transicionar(anterior, Estado.EN_CAMINO)
        pedido.salida_id = salida_id
        _evento(
            sesion,
            pedido,
            "estado",
            quien,
            de=anterior,
            a=Estado.EN_CAMINO,
            salida_id=str(salida_id),
        )
    await sesion.flush()


async def publicar_despacho(pedidos: Sequence[Pedido]) -> None:
    for pedido in pedidos:
        await _publicar(pedido, "pedido.estado")


async def modelos_de_salida(sesion: AsyncSession, salida_id: uuid.UUID) -> list[Pedido]:
    return list(await repository.listar(sesion, sucursal_id=None, salida_id=salida_id, limite=2000))


# ---------- para cobros ----------


async def a_cuenta_de_cliente(sesion: AsyncSession, cliente_id: uuid.UUID) -> list[Pedido]:
    """Todos los pedidos a cuenta del cliente (incluye cancelados: el extracto los revierte)."""
    pedidos = await repository.listar(sesion, sucursal_id=None, cliente_id=cliente_id, limite=5000)
    return [p for p in pedidos if p.a_cuenta]


async def marcar_pagados(
    sesion: AsyncSession, quien: Identidad, pedidos: Sequence[Pedido], pago_id: uuid.UUID
) -> None:
    """No commitea: viaja en la transacción del cobro."""
    for pedido in pedidos:
        pedido.pagado = True
        _evento(sesion, pedido, "pagado", quien, pago_id=str(pago_id))
