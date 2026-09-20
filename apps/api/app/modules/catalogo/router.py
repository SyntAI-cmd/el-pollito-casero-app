import uuid

from fastapi import APIRouter

from app.core.db import Sesion
from app.core.dependencias import Equipo, SoloAdmin
from app.domain.precios import Lista, Turno
from app.modules.catalogo import service
from app.modules.catalogo.schemas import (
    ListasEntrada,
    PrecioListaSalida,
    ProductoCambios,
    ProductoSalida,
)

router = APIRouter(tags=["catalogo"])


@router.get("/productos", response_model=list[ProductoSalida])
async def listar_productos(
    sesion: Sesion, quien: Equipo, incluir_inactivos: bool = False
) -> list[ProductoSalida]:
    productos = await service.listar_productos(sesion, solo_activos=not incluir_inactivos)
    return [ProductoSalida.model_validate(p) for p in productos]


@router.patch("/productos/{producto_id}", response_model=ProductoSalida)
async def modificar_producto(
    producto_id: uuid.UUID, cambios: ProductoCambios, sesion: Sesion, quien: SoloAdmin
) -> ProductoSalida:
    return ProductoSalida.model_validate(
        await service.modificar_producto(sesion, quien, producto_id, cambios)
    )


@router.get("/precios/listas", response_model=list[PrecioListaSalida])
async def listar_listas(
    sucursal_id: uuid.UUID,
    sesion: Sesion,
    quien: Equipo,
    lista: Lista | None = None,
    turno: Turno | None = None,
) -> list[PrecioListaSalida]:
    return await service.listar_listas(sesion, quien, sucursal_id, lista, turno)


@router.put("/precios/listas", response_model=list[PrecioListaSalida])
async def guardar_listas(
    datos: ListasEntrada, sesion: Sesion, quien: SoloAdmin
) -> list[PrecioListaSalida]:
    return await service.guardar_listas(sesion, quien, datos)
