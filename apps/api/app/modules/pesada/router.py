import uuid

from fastapi import APIRouter, status

from app.core.db import Sesion
from app.core.dependencias import Operativo
from app.modules.pedidos.schemas import PedidoSalida
from app.modules.pesada import service
from app.modules.pesada.schemas import AnulacionEntrada, CajonEntrada, CajonSalida, LoteEntrada

router = APIRouter(tags=["pesada"])


@router.get("/pedidos/{pedido_id}/cajones", response_model=list[CajonSalida])
async def cajones(pedido_id: uuid.UUID, sesion: Sesion, quien: Operativo) -> list[CajonSalida]:
    return await service.cajones_de(sesion, quien, pedido_id)


@router.post(
    "/pedidos/{pedido_id}/cajones", response_model=PedidoSalida, status_code=status.HTTP_201_CREATED
)
async def pesar_cajon(
    pedido_id: uuid.UUID, datos: CajonEntrada, sesion: Sesion, quien: Operativo
) -> PedidoSalida:
    """Un cajón: bruto tipeado, el servidor resta la tara de la sucursal."""
    return await service.pesar_cajon(sesion, quien, pedido_id, datos)


@router.post(
    "/pedidos/{pedido_id}/cajones/lote",
    response_model=PedidoSalida,
    status_code=status.HTTP_201_CREATED,
)
async def pesar_lote(
    pedido_id: uuid.UUID, datos: LoteEntrada, sesion: Sesion, quien: Operativo
) -> PedidoSalida:
    """N cajas con un bruto total: el servidor reparte el neto y crea un cajón por caja."""
    return await service.pesar_lote(sesion, quien, pedido_id, datos)


@router.post("/cajones/{cajon_id}/anular", response_model=PedidoSalida)
async def anular(
    cajon_id: uuid.UUID, datos: AnulacionEntrada, sesion: Sesion, quien: Operativo
) -> PedidoSalida:
    return await service.anular(sesion, quien, cajon_id, datos.motivo)


@router.post("/cajones/{cajon_id}/cargar", response_model=PedidoSalida)
async def cargar(cajon_id: uuid.UUID, sesion: Sesion, quien: Operativo) -> PedidoSalida:
    return await service.cargar(sesion, quien, cajon_id, cargado=True)


@router.post("/cajones/{cajon_id}/descargar", response_model=PedidoSalida)
async def descargar(cajon_id: uuid.UUID, sesion: Sesion, quien: Operativo) -> PedidoSalida:
    return await service.cargar(sesion, quien, cajon_id, cargado=False)
