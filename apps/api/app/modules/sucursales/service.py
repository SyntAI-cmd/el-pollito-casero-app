import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errores import Conflicto, NoEncontrado, SinPermiso
from app.core.seguridad import Identidad, Rol
from app.modules.auditoria.service import registrar
from app.modules.sucursales import repository
from app.modules.sucursales.models import Sucursal, Zona
from app.modules.sucursales.schemas import (
    SucursalCambios,
    SucursalEntrada,
    ZonaCambios,
    ZonaEntrada,
)


def verificar_sucursal(quien: Identidad, sucursal_id: uuid.UUID) -> None:
    """Todo se filtra por sucursal: solo admin cruza de una a otra."""
    if quien.rol is not Rol.ADMIN and quien.sucursal_id != sucursal_id:
        raise SinPermiso("Esa sucursal no es la tuya")


async def listar(sesion: AsyncSession, quien: Identidad) -> list[Sucursal]:
    sucursales = await repository.listar_sucursales(sesion)
    if quien.rol is Rol.ADMIN:
        return list(sucursales)
    return [s for s in sucursales if s.id == quien.sucursal_id]


async def obtener(sesion: AsyncSession, quien: Identidad, sucursal_id: uuid.UUID) -> Sucursal:
    verificar_sucursal(quien, sucursal_id)
    sucursal = await repository.sucursal_por_id(sesion, sucursal_id)
    if sucursal is None:
        raise NoEncontrado("Sucursal")
    return sucursal


async def crear(sesion: AsyncSession, quien: Identidad, datos: SucursalEntrada) -> Sucursal:
    if await repository.sucursal_por_nombre(sesion, datos.nombre.strip()):
        raise Conflicto(f"Ya existe la sucursal {datos.nombre}")
    sucursal = Sucursal(nombre=datos.nombre.strip(), direccion=datos.direccion.strip())
    sesion.add(sucursal)
    await sesion.flush()
    registrar(sesion, quien, "sucursal.crear", "sucursal", sucursal.id)
    await sesion.commit()
    return sucursal


async def modificar(
    sesion: AsyncSession, quien: Identidad, sucursal_id: uuid.UUID, cambios: SucursalCambios
) -> Sucursal:
    sucursal = await obtener(sesion, quien, sucursal_id)
    for campo, valor in cambios.model_dump(exclude_unset=True).items():
        setattr(sucursal, campo, valor.strip() if isinstance(valor, str) else valor)
    registrar(sesion, quien, "sucursal.modificar", "sucursal", sucursal.id)
    await sesion.commit()
    return sucursal


async def listar_zonas(
    sesion: AsyncSession, quien: Identidad, sucursal_id: uuid.UUID
) -> list[Zona]:
    verificar_sucursal(quien, sucursal_id)
    return list(await repository.listar_zonas(sesion, sucursal_id))


async def crear_zona(
    sesion: AsyncSession, quien: Identidad, sucursal_id: uuid.UUID, datos: ZonaEntrada
) -> Zona:
    await obtener(sesion, quien, sucursal_id)
    if await repository.zona_por_nombre(sesion, sucursal_id, datos.nombre.strip()):
        raise Conflicto(f"Ya existe la zona {datos.nombre} en esta sucursal")
    zona = Zona(sucursal_id=sucursal_id, nombre=datos.nombre.strip())
    sesion.add(zona)
    await sesion.flush()
    registrar(sesion, quien, "zona.crear", "zona", zona.id)
    await sesion.commit()
    return zona


async def modificar_zona(
    sesion: AsyncSession, quien: Identidad, zona_id: uuid.UUID, cambios: ZonaCambios
) -> Zona:
    zona = await repository.zona_por_id(sesion, zona_id)
    if zona is None:
        raise NoEncontrado("Zona")
    verificar_sucursal(quien, zona.sucursal_id)
    for campo, valor in cambios.model_dump(exclude_unset=True).items():
        setattr(zona, campo, valor.strip() if isinstance(valor, str) else valor)
    registrar(sesion, quien, "zona.modificar", "zona", zona.id)
    await sesion.commit()
    return zona
