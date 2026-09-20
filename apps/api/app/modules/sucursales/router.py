import uuid

from fastapi import APIRouter, status

from app.core.db import Sesion
from app.core.dependencias import Equipo, SoloAdmin
from app.modules.sucursales import service
from app.modules.sucursales.schemas import (
    SucursalCambios,
    SucursalEntrada,
    SucursalSalida,
    ZonaCambios,
    ZonaEntrada,
    ZonaSalida,
)

router = APIRouter(tags=["sucursales"])


@router.get("/sucursales", response_model=list[SucursalSalida])
async def listar(sesion: Sesion, quien: Equipo) -> list[SucursalSalida]:
    return [SucursalSalida.model_validate(s) for s in await service.listar(sesion, quien)]


@router.post("/sucursales", response_model=SucursalSalida, status_code=status.HTTP_201_CREATED)
async def crear(datos: SucursalEntrada, sesion: Sesion, quien: SoloAdmin) -> SucursalSalida:
    return SucursalSalida.model_validate(await service.crear(sesion, quien, datos))


@router.patch("/sucursales/{sucursal_id}", response_model=SucursalSalida)
async def modificar(
    sucursal_id: uuid.UUID, cambios: SucursalCambios, sesion: Sesion, quien: SoloAdmin
) -> SucursalSalida:
    return SucursalSalida.model_validate(
        await service.modificar(sesion, quien, sucursal_id, cambios)
    )


@router.get("/sucursales/{sucursal_id}/zonas", response_model=list[ZonaSalida])
async def listar_zonas(sucursal_id: uuid.UUID, sesion: Sesion, quien: Equipo) -> list[ZonaSalida]:
    zonas = await service.listar_zonas(sesion, quien, sucursal_id)
    return [ZonaSalida.model_validate(z) for z in zonas]


@router.post(
    "/sucursales/{sucursal_id}/zonas",
    response_model=ZonaSalida,
    status_code=status.HTTP_201_CREATED,
)
async def crear_zona(
    sucursal_id: uuid.UUID, datos: ZonaEntrada, sesion: Sesion, quien: SoloAdmin
) -> ZonaSalida:
    return ZonaSalida.model_validate(await service.crear_zona(sesion, quien, sucursal_id, datos))


@router.patch("/zonas/{zona_id}", response_model=ZonaSalida)
async def modificar_zona(
    zona_id: uuid.UUID, cambios: ZonaCambios, sesion: Sesion, quien: SoloAdmin
) -> ZonaSalida:
    return ZonaSalida.model_validate(await service.modificar_zona(sesion, quien, zona_id, cambios))
