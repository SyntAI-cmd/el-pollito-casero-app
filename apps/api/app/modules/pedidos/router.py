import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.db import Sesion
from app.core.dependencias import Operativo, SoloAdmin
from app.core.paginacion import Pagina, pagina
from app.domain.pedidos import Estado
from app.domain.precios import Turno
from app.modules.pedidos import service
from app.modules.pedidos.schemas import (
    EstadoEntrada,
    EventoSalida,
    NotaDelDia,
    PedidoCambios,
    PedidoEntrada,
    PedidoSalida,
    PreciosPedidoEntrada,
)

router = APIRouter(tags=["pedidos"])


@router.get("/pedidos", response_model=list[PedidoSalida])
async def listar(
    sesion: Sesion,
    quien: Operativo,
    pag: Annotated[Pagina, Depends(pagina)],
    fecha: date | None = None,
    turno: Turno | None = None,
    estado: Estado | None = None,
    cliente_id: uuid.UUID | None = None,
    preventista_id: uuid.UUID | None = None,
) -> list[PedidoSalida]:
    return await service.listar(
        sesion, quien, fecha, turno, estado, cliente_id, preventista_id, pag.limite, pag.desde
    )


@router.post("/pedidos", response_model=PedidoSalida, status_code=status.HTTP_201_CREATED)
async def crear(datos: PedidoEntrada, sesion: Sesion, quien: Operativo) -> PedidoSalida:
    return await service.crear(sesion, quien, datos)


@router.get("/pedidos/dia", response_model=NotaDelDia)
async def nota_del_dia(
    fecha: date, sesion: Sesion, quien: Operativo, turno: Turno | None = None
) -> NotaDelDia:
    return await service.nota_del_dia(sesion, quien, fecha, turno)


@router.get("/pedidos/{pedido_id}", response_model=PedidoSalida)
async def obtener(pedido_id: uuid.UUID, sesion: Sesion, quien: Operativo) -> PedidoSalida:
    return await service.obtener(sesion, quien, pedido_id)


@router.patch("/pedidos/{pedido_id}", response_model=PedidoSalida)
async def modificar(
    pedido_id: uuid.UUID, cambios: PedidoCambios, sesion: Sesion, quien: Operativo
) -> PedidoSalida:
    return await service.modificar(sesion, quien, pedido_id, cambios)


@router.put("/pedidos/{pedido_id}/precios", response_model=PedidoSalida)
async def cambiar_precios(
    pedido_id: uuid.UUID, datos: PreciosPedidoEntrada, sesion: Sesion, quien: Operativo
) -> PedidoSalida:
    return await service.cambiar_precios(sesion, quien, pedido_id, datos)


@router.post("/pedidos/{pedido_id}/estado", response_model=PedidoSalida)
async def cambiar_estado(
    pedido_id: uuid.UUID, datos: EstadoEntrada, sesion: Sesion, quien: Operativo
) -> PedidoSalida:
    return await service.cambiar_estado(sesion, quien, pedido_id, datos)


@router.delete("/pedidos/{pedido_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar(pedido_id: uuid.UUID, sesion: Sesion, quien: SoloAdmin) -> None:
    await service.eliminar(sesion, quien, pedido_id)


@router.get("/pedidos/{pedido_id}/eventos", response_model=list[EventoSalida])
async def eventos(pedido_id: uuid.UUID, sesion: Sesion, quien: Operativo) -> list[EventoSalida]:
    return [EventoSalida.model_validate(e) for e in await service.eventos(sesion, quien, pedido_id)]
