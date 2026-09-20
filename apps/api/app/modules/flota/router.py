import uuid
from datetime import date

from fastapi import APIRouter, status

from app.core.db import Sesion
from app.core.dependencias import Equipo, Operativo, SoloAdmin
from app.modules.flota import service
from app.modules.flota.schemas import (
    CierreEntrada,
    PosicionEntrada,
    PosicionSalida,
    SalidaEntrada,
    SalidaSalida,
    VehiculoCambios,
    VehiculoEntrada,
    VehiculoSalida,
)

router = APIRouter(tags=["flota"])


@router.get("/vehiculos", response_model=list[VehiculoSalida])
async def listar_vehiculos(
    sesion: Sesion, quien: Equipo, incluir_inactivos: bool = False
) -> list[VehiculoSalida]:
    vehiculos = await service.listar_vehiculos(sesion, quien, incluir_inactivos)
    return [VehiculoSalida.model_validate(v) for v in vehiculos]


@router.post("/vehiculos", response_model=VehiculoSalida, status_code=status.HTTP_201_CREATED)
async def crear_vehiculo(
    datos: VehiculoEntrada, sesion: Sesion, quien: SoloAdmin
) -> VehiculoSalida:
    return VehiculoSalida.model_validate(await service.crear_vehiculo(sesion, quien, datos))


@router.patch("/vehiculos/{vehiculo_id}", response_model=VehiculoSalida)
async def modificar_vehiculo(
    vehiculo_id: uuid.UUID, cambios: VehiculoCambios, sesion: Sesion, quien: SoloAdmin
) -> VehiculoSalida:
    return VehiculoSalida.model_validate(
        await service.modificar_vehiculo(sesion, quien, vehiculo_id, cambios)
    )


@router.get("/salidas", response_model=list[SalidaSalida])
async def listar_salidas(fecha: date, sesion: Sesion, quien: Operativo) -> list[SalidaSalida]:
    """Flota en vivo: cada camión del día con quiénes van, cuántos pedidos y última posición."""
    return await service.listar_salidas(sesion, quien, fecha)


@router.put("/salidas", response_model=SalidaSalida)
async def guardar_salida(datos: SalidaEntrada, sesion: Sesion, quien: Operativo) -> SalidaSalida:
    return await service.guardar_salida(sesion, quien, datos)


@router.get("/salidas/{salida_id}", response_model=SalidaSalida)
async def obtener_salida(salida_id: uuid.UUID, sesion: Sesion, quien: Operativo) -> SalidaSalida:
    return await service.obtener_salida(sesion, quien, salida_id)


@router.post("/salidas/{salida_id}/cerrar", response_model=SalidaSalida)
async def cerrar_camion(
    salida_id: uuid.UUID, datos: CierreEntrada, sesion: Sesion, quien: Operativo
) -> SalidaSalida:
    """Cerrar camión: avisa si falta pesar o cargar y pide motivo para salir igual."""
    return await service.cerrar_camion(sesion, quien, salida_id, datos.motivo)


@router.post("/salidas/{salida_id}/ubicacion", status_code=status.HTTP_204_NO_CONTENT)
async def registrar_posicion(
    salida_id: uuid.UUID, datos: PosicionEntrada, sesion: Sesion, quien: Operativo
) -> None:
    await service.registrar_posicion(sesion, quien, salida_id, datos)


@router.get("/salidas/{salida_id}/recorrido", response_model=list[PosicionSalida])
async def recorrido(salida_id: uuid.UUID, sesion: Sesion, quien: Operativo) -> list[PosicionSalida]:
    return await service.recorrido(sesion, quien, salida_id)
