import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errores import Conflicto, NoEncontrado, SinPermiso
from app.core.seguridad import Identidad, Rol
from app.core.tiempo import ahora
from app.domain.errores import ErrorDominio
from app.domain.precios import resolver_precio, validar_precio
from app.domain.saldos import MovimientoEnvases as EnvasesDominio
from app.domain.saldos import saldo_envases
from app.domain.telefonos import normalizar_telefono
from app.integrations.maps import geocodificador
from app.modules.auditoria.service import registrar
from app.modules.catalogo import service as catalogo
from app.modules.clientes import repository
from app.modules.clientes.models import Cliente, EstadoFicha, MovimientoEnvases, PrecioCliente
from app.modules.clientes.schemas import (
    ClienteCambios,
    ClienteEntrada,
    EnvasesSalida,
    MovimientoEnvasesEntrada,
    MovimientoEnvasesSalida,
    PrecioResuelto,
    PreciosPropiosEntrada,
)
from app.modules.sucursales.service import verificar_sucursal


def _puede_ver(quien: Identidad, cliente: Cliente) -> bool:
    """El filtrado por rol se hace acá, no en la interfaz."""
    if quien.rol is Rol.ADMIN:
        return True
    if cliente.sucursal_id != quien.sucursal_id:
        return False
    if quien.rol is Rol.PREVENTISTA:
        return cliente.preventista_id in (None, quien.usuario_id)
    if quien.rol is Rol.COBRADOR:
        return cliente.cobrador_id == quien.usuario_id
    return False


async def obtener(sesion: AsyncSession, quien: Identidad, cliente_id: uuid.UUID) -> Cliente:
    cliente = await repository.por_id(sesion, cliente_id)
    if cliente is None or not _puede_ver(quien, cliente):
        # Mismo 404 para "no existe" y "no es tuyo": no se revela qué clientes hay.
        raise NoEncontrado("Cliente")
    return cliente


async def listar(
    sesion: AsyncSession,
    quien: Identidad,
    texto: str | None,
    zona_id: uuid.UUID | None,
    preventista_id: uuid.UUID | None,
    incluir_inactivos: bool,
    limite: int,
    desde: int,
) -> list[Cliente]:
    return list(
        await repository.listar(
            sesion,
            sucursal_id=None if quien.rol is Rol.ADMIN else quien.sucursal_id,
            texto=texto,
            zona_id=zona_id,
            preventista_id=preventista_id,
            solo_de_preventista=quien.usuario_id if quien.rol is Rol.PREVENTISTA else None,
            solo_de_cobrador=quien.usuario_id if quien.rol is Rol.COBRADOR else None,
            incluir_inactivos=incluir_inactivos and quien.rol is Rol.ADMIN,
            limite=limite,
            desde=desde,
        )
    )


def _estado_ficha(cliente: Cliente) -> EstadoFicha:
    if not cliente.cuit:
        return EstadoFicha.SIN_CUIT
    if not cliente.direccion or cliente.lat is None:
        return EstadoFicha.REVISAR
    return EstadoFicha.COMPLETA


async def _validar_telefono(
    sesion: AsyncSession, telefono: str | None, salvo: uuid.UUID | None
) -> str | None:
    if not telefono:
        return None
    normalizado = normalizar_telefono(telefono)
    if normalizado is None:
        raise ErrorDominio("Teléfono inválido: escribilo con código de área")
    existente = await repository.por_telefono(sesion, normalizado)
    if existente is not None and existente.id != salvo:
        raise Conflicto(f"Ese teléfono ya es de {existente.nombre_comercial}")
    return normalizado


async def _geocodificar_si_falta(cliente: Cliente) -> None:
    if cliente.lat is not None or not cliente.direccion:
        return
    coordenadas = await geocodificador().geocodificar(cliente.direccion, cliente.localidad)
    if coordenadas is not None:
        cliente.lat, cliente.lng = coordenadas.lat, coordenadas.lng


async def crear(sesion: AsyncSession, quien: Identidad, datos: ClienteEntrada) -> Cliente:
    if quien.rol not in (Rol.ADMIN, Rol.PREVENTISTA):
        raise SinPermiso("Solo administración y preventistas cargan clientes")
    sucursal_id = datos.sucursal_id or quien.sucursal_id
    verificar_sucursal(quien, sucursal_id)
    if datos.codigo and await repository.por_codigo(sesion, sucursal_id, datos.codigo):
        raise Conflicto(f"Ya existe un cliente con código {datos.codigo}")
    cliente = Cliente(
        sucursal_id=sucursal_id,
        codigo=datos.codigo,
        razon_social=datos.razon_social.strip(),
        nombre_comercial=(datos.nombre_comercial or datos.razon_social).strip(),
        cuit=datos.cuit,
        telefono=await _validar_telefono(sesion, datos.telefono, None),
        direccion=datos.direccion.strip(),
        localidad=datos.localidad.strip(),
        lat=datos.lat,
        lng=datos.lng,
        zona_id=datos.zona_id,
        lista=datos.lista,
        turno=datos.turno,
        # Un preventista que carga un cliente desde el celular se lo queda asignado.
        preventista_id=datos.preventista_id
        or (quien.usuario_id if quien.rol is Rol.PREVENTISTA else None),
        cobrador_id=datos.cobrador_id,
        credito_habilitado=datos.credito_habilitado,
        observaciones=datos.observaciones.strip(),
    )
    await _geocodificar_si_falta(cliente)
    cliente.estado_ficha = _estado_ficha(cliente)
    sesion.add(cliente)
    await sesion.flush()
    registrar(sesion, quien, "cliente.crear", "cliente", cliente.id)
    await sesion.commit()
    return cliente


async def modificar(
    sesion: AsyncSession, quien: Identidad, cliente_id: uuid.UUID, cambios: ClienteCambios
) -> Cliente:
    if quien.rol not in (Rol.ADMIN, Rol.PREVENTISTA):
        raise SinPermiso("Solo administración y preventistas editan fichas")
    cliente = await obtener(sesion, quien, cliente_id)
    datos = cambios.model_dump(exclude_unset=True)
    if quien.rol is not Rol.ADMIN:
        for campo in ("ajuste_envases", "activo", "credito_habilitado", "cobrador_id"):
            if campo in datos:
                raise SinPermiso(f"Solo administración cambia {campo}")
    if "telefono" in datos:
        datos["telefono"] = await _validar_telefono(sesion, datos["telefono"], cliente.id)
    if "codigo" in datos and datos["codigo"]:
        otro = await repository.por_codigo(sesion, cliente.sucursal_id, datos["codigo"])
        if otro is not None and otro.id != cliente.id:
            raise Conflicto(f"Ya existe un cliente con código {datos['codigo']}")
    if "direccion" in datos and datos["direccion"] != cliente.direccion and "lat" not in datos:
        cliente.lat = cliente.lng = None  # cambió la dirección: se vuelve a geocodificar
    for campo, valor in datos.items():
        setattr(cliente, campo, valor.strip() if isinstance(valor, str) else valor)
    await _geocodificar_si_falta(cliente)
    if "estado_ficha" not in datos:
        cliente.estado_ficha = _estado_ficha(cliente)
    registrar(sesion, quien, "cliente.modificar", "cliente", cliente.id, {"campos": sorted(datos)})
    await sesion.commit()
    return cliente


async def precios_resueltos(
    sesion: AsyncSession, quien: Identidad, cliente_id: uuid.UUID
) -> list[PrecioResuelto]:
    """Por producto: el precio propio, el de lista (turno + zona del cliente) o "sin precio"."""
    cliente = await obtener(sesion, quien, cliente_id)
    productos = await catalogo.listar_productos(sesion)
    por_id = {p.id: p.codigo for p in productos}
    propios = {
        por_id[f.producto_id]: f.precio
        for f in await repository.precios_propios(sesion, cliente.id)
        if f.producto_id in por_id
    }
    listas = await catalogo.listas_como_dominio(
        sesion, cliente.sucursal_id, cliente.lista, cliente.turno
    )
    zona = str(cliente.zona_id) if cliente.zona_id else None
    salida: list[PrecioResuelto] = []
    for producto in productos:
        precio = resolver_precio(
            producto.codigo, propios, listas, cliente.lista, cliente.turno, zona
        )
        origen = "propio" if producto.codigo in propios else "lista" if precio else "sin_precio"
        salida.append(
            PrecioResuelto(
                producto_codigo=producto.codigo,
                producto_nombre=producto.nombre,
                precio=precio,
                origen=origen,
            )
        )
    return salida


async def precios_propios_como_mapa(
    sesion: AsyncSession, cliente_id: uuid.UUID
) -> dict[str, Decimal]:
    por_id = {p.id: p.codigo for p in await catalogo.listar_productos(sesion, solo_activos=False)}
    return {
        por_id[f.producto_id]: f.precio
        for f in await repository.precios_propios(sesion, cliente_id)
        if f.producto_id in por_id
    }


async def guardar_precios_propios(
    sesion: AsyncSession,
    quien: Identidad,
    cliente_id: uuid.UUID,
    datos: PreciosPropiosEntrada,
    commit: bool = True,
) -> list[PrecioResuelto]:
    """Cualquier usuario del equipo con acceso al cliente. Precio nulo = borrar el propio."""
    cliente = await obtener(sesion, quien, cliente_id)
    por_codigo = await catalogo.productos_por_codigo(sesion)
    cambios: dict[str, str | None] = {}
    for entrada in datos.precios:
        producto = por_codigo.get(entrada.producto_codigo)
        if producto is None:
            raise ErrorDominio(f"Producto desconocido: {entrada.producto_codigo}")
        fila = await repository.precio_propio(sesion, cliente.id, producto.id)
        if entrada.precio is None:
            if fila is not None:
                await sesion.delete(fila)
            cambios[producto.codigo] = None
            continue
        precio = validar_precio(entrada.precio)
        if fila is None:
            sesion.add(PrecioCliente(cliente_id=cliente.id, producto_id=producto.id, precio=precio))
        else:
            fila.precio = precio
        cambios[producto.codigo] = str(precio)
    registrar(sesion, quien, "cliente.precios", "cliente", cliente.id, {"precios": cambios})
    if commit:
        await sesion.commit()
    else:
        await sesion.flush()
    return await precios_resueltos(sesion, quien, cliente_id)


async def envases(sesion: AsyncSession, quien: Identidad, cliente_id: uuid.UUID) -> EnvasesSalida:
    cliente = await obtener(sesion, quien, cliente_id)
    filas = await repository.movimientos_envases(sesion, cliente.id)
    saldo = saldo_envases(
        [EnvasesDominio(f.fecha, f.dejados, f.devueltos, str(f.id)) for f in filas],
        ajuste=cliente.ajuste_envases,
    )
    return EnvasesSalida(
        saldo=saldo,
        ajuste=cliente.ajuste_envases,
        movimientos=[MovimientoEnvasesSalida.model_validate(f) for f in filas],
    )


async def registrar_envases(
    sesion: AsyncSession, quien: Identidad, cliente_id: uuid.UUID, datos: MovimientoEnvasesEntrada
) -> EnvasesSalida:
    cliente = await obtener(sesion, quien, cliente_id)
    if datos.dejados == 0 and datos.devueltos == 0:
        raise ErrorDominio("Indicá cajones dejados o devueltos")
    fila = MovimientoEnvases(
        sucursal_id=cliente.sucursal_id,
        cliente_id=cliente.id,
        pedido_id=datos.pedido_id,
        fecha=ahora(),
        dejados=datos.dejados,
        devueltos=datos.devueltos,
        nota=datos.nota.strip(),
        registrado_por=quien.usuario_id,
    )
    sesion.add(fila)
    await sesion.flush()
    registrar(
        sesion,
        quien,
        "envases.movimiento",
        "cliente",
        cliente.id,
        {"dejados": datos.dejados, "devueltos": datos.devueltos},
    )
    await sesion.commit()
    return await envases(sesion, quien, cliente_id)


async def obtener_interno(sesion: AsyncSession, cliente_id: uuid.UUID) -> Cliente:
    """Para otros services que ya verificaron el permiso sobre el pedido o el cobro."""
    cliente = await repository.por_id(sesion, cliente_id)
    if cliente is None:
        raise NoEncontrado("Cliente")
    return cliente


async def ajustar_saldo_a_favor(
    sesion: AsyncSession, quien: Identidad, cliente_id: uuid.UUID, delta: Decimal, motivo: str
) -> Cliente:
    """Suma (o resta) saldo a favor. No commitea: viaja en la transacción de quien lo llama."""
    cliente = await obtener_interno(sesion, cliente_id)
    anterior = cliente.saldo_a_favor
    cliente.saldo_a_favor = anterior + delta
    registrar(
        sesion,
        quien,
        "cliente.saldo_a_favor",
        "cliente",
        cliente.id,
        {"anterior": str(anterior), "delta": str(delta), "motivo": motivo},
    )
    return cliente
