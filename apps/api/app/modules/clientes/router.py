import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.db import Sesion
from app.core.dependencias import Equipo, Operativo
from app.core.paginacion import Pagina, pagina
from app.modules.clientes import service
from app.modules.clientes.schemas import (
    ClienteCambios,
    ClienteEntrada,
    ClienteSalida,
    EnvasesSalida,
    MovimientoEnvasesEntrada,
    PrecioResuelto,
    PreciosPropiosEntrada,
)

router = APIRouter(prefix="/clientes", tags=["clientes"])


@router.get("", response_model=list[ClienteSalida])
async def listar(
    sesion: Sesion,
    quien: Equipo,
    pag: Annotated[Pagina, Depends(pagina)],
    q: Annotated[str | None, Query(max_length=80)] = None,
    zona_id: uuid.UUID | None = None,
    preventista_id: uuid.UUID | None = None,
    incluir_inactivos: bool = False,
) -> list[ClienteSalida]:
    clientes = await service.listar(
        sesion, quien, q, zona_id, preventista_id, incluir_inactivos, pag.limite, pag.desde
    )
    return [ClienteSalida.model_validate(c) for c in clientes]


@router.post("", response_model=ClienteSalida, status_code=status.HTTP_201_CREATED)
async def crear(datos: ClienteEntrada, sesion: Sesion, quien: Operativo) -> ClienteSalida:
    return ClienteSalida.model_validate(await service.crear(sesion, quien, datos))


@router.get("/{cliente_id}", response_model=ClienteSalida)
async def obtener(cliente_id: uuid.UUID, sesion: Sesion, quien: Equipo) -> ClienteSalida:
    return ClienteSalida.model_validate(await service.obtener(sesion, quien, cliente_id))


@router.patch("/{cliente_id}", response_model=ClienteSalida)
async def modificar(
    cliente_id: uuid.UUID, cambios: ClienteCambios, sesion: Sesion, quien: Operativo
) -> ClienteSalida:
    return ClienteSalida.model_validate(await service.modificar(sesion, quien, cliente_id, cambios))


@router.get("/{cliente_id}/precios", response_model=list[PrecioResuelto])
async def precios(cliente_id: uuid.UUID, sesion: Sesion, quien: Equipo) -> list[PrecioResuelto]:
    return await service.precios_resueltos(sesion, quien, cliente_id)


@router.put("/{cliente_id}/precios", response_model=list[PrecioResuelto])
async def guardar_precios(
    cliente_id: uuid.UUID, datos: PreciosPropiosEntrada, sesion: Sesion, quien: Operativo
) -> list[PrecioResuelto]:
    return await service.guardar_precios_propios(sesion, quien, cliente_id, datos)


@router.get("/{cliente_id}/envases", response_model=EnvasesSalida)
async def envases(cliente_id: uuid.UUID, sesion: Sesion, quien: Equipo) -> EnvasesSalida:
    return await service.envases(sesion, quien, cliente_id)


@router.post("/{cliente_id}/envases", response_model=EnvasesSalida)
async def registrar_envases(
    cliente_id: uuid.UUID, datos: MovimientoEnvasesEntrada, sesion: Sesion, quien: Equipo
) -> EnvasesSalida:
    return await service.registrar_envases(sesion, quien, cliente_id, datos)
