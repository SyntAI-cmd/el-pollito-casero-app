import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errores import NoEncontrado
from app.core.seguridad import Identidad
from app.domain.errores import ErrorDominio
from app.domain.precios import Lista, PrecioLista, Turno, validar_precio
from app.modules.auditoria.service import registrar
from app.modules.catalogo import repository
from app.modules.catalogo.models import ListaPrecio, Producto
from app.modules.catalogo.schemas import ListasEntrada, PrecioListaSalida, ProductoCambios
from app.modules.sucursales.service import verificar_sucursal


async def listar_productos(sesion: AsyncSession, solo_activos: bool = True) -> list[Producto]:
    return list(await repository.listar_productos(sesion, solo_activos))


async def productos_por_codigo(sesion: AsyncSession) -> dict[str, Producto]:
    return await repository.productos_por_codigo(sesion)


async def modificar_producto(
    sesion: AsyncSession, quien: Identidad, producto_id: uuid.UUID, cambios: ProductoCambios
) -> Producto:
    producto = await repository.producto_por_id(sesion, producto_id)
    if producto is None:
        raise NoEncontrado("Producto")
    for campo, valor in cambios.model_dump(exclude_unset=True).items():
        setattr(producto, campo, valor)
    registrar(sesion, quien, "producto.modificar", "producto", producto.id)
    await sesion.commit()
    return producto


def _a_salida(fila: ListaPrecio, codigo: str) -> PrecioListaSalida:
    return PrecioListaSalida(
        id=fila.id,
        sucursal_id=fila.sucursal_id,
        producto_codigo=codigo,
        lista=fila.lista,
        turno=fila.turno,
        zona_id=fila.zona_id,
        precio=fila.precio,
    )


async def listar_listas(
    sesion: AsyncSession,
    quien: Identidad,
    sucursal_id: uuid.UUID,
    lista: Lista | None,
    turno: Turno | None,
) -> list[PrecioListaSalida]:
    verificar_sucursal(quien, sucursal_id)
    productos = {p.id: p.codigo for p in await repository.listar_productos(sesion, False)}
    filas = await repository.listas_de(sesion, sucursal_id, lista, turno)
    return [_a_salida(f, productos[f.producto_id]) for f in filas]


async def listas_como_dominio(
    sesion: AsyncSession, sucursal_id: uuid.UUID, lista: Lista, turno: Turno
) -> list[PrecioLista]:
    """Lo que consumen clientes y pedidos para resolver precios con las reglas del dominio."""
    productos = {p.id: p.codigo for p in await repository.listar_productos(sesion, False)}
    return [
        PrecioLista(
            producto_id=productos[f.producto_id],
            lista=f.lista,
            turno=f.turno,
            precio=f.precio,
            zona_id=str(f.zona_id) if f.zona_id else None,
        )
        for f in await repository.listas_de(sesion, sucursal_id, lista, turno)
    ]


async def guardar_listas(
    sesion: AsyncSession, quien: Identidad, datos: ListasEntrada
) -> list[PrecioListaSalida]:
    """Alta o actualización por (producto, lista, turno, zona). Los precios propios no se tocan."""
    verificar_sucursal(quien, datos.sucursal_id)
    por_codigo = await repository.productos_por_codigo(sesion)
    guardadas: list[PrecioListaSalida] = []
    for entrada in datos.precios:
        producto = por_codigo.get(entrada.producto_codigo)
        if producto is None:
            raise ErrorDominio(f"Producto desconocido: {entrada.producto_codigo}")
        precio = validar_precio(entrada.precio)
        fila = await repository.fila_de_lista(
            sesion, datos.sucursal_id, producto.id, entrada.lista, entrada.turno, entrada.zona_id
        )
        if fila is None:
            fila = ListaPrecio(
                sucursal_id=datos.sucursal_id,
                producto_id=producto.id,
                lista=entrada.lista,
                turno=entrada.turno,
                zona_id=entrada.zona_id,
                precio=precio,
            )
            sesion.add(fila)
            await sesion.flush()
        else:
            fila.precio = precio
        guardadas.append(_a_salida(fila, producto.codigo))
    registrar(
        sesion,
        quien,
        "listas_precio.guardar",
        "sucursal",
        datos.sucursal_id,
        {"cantidad": len(guardadas)},
    )
    await sesion.commit()
    return guardadas
