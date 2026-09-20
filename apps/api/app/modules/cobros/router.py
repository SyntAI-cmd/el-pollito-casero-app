import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, File, Form, Query, Response, UploadFile, status

from app.core.db import Sesion
from app.core.dependencias import Equipo, Operativo, SoloAdmin
from app.integrations.storage import firma_valida, storage
from app.modules.cobros import service
from app.modules.cobros.models import TipoComprobante
from app.modules.cobros.schemas import (
    AjusteEntrada,
    CierreEntrada,
    CierreSalida,
    ComprobanteSalida,
    CuentaACobrar,
    ExtractoSalida,
    PagoEntrada,
    PagoSalida,
    ResumenCaja,
)

router = APIRouter(tags=["cobros"])


@router.post("/comprobantes", response_model=ComprobanteSalida, status_code=status.HTTP_201_CREATED)
async def subir_comprobante(
    sesion: Sesion,
    quien: Equipo,
    archivo: Annotated[UploadFile, File()],
    tipo: Annotated[TipoComprobante, Form()] = TipoComprobante.COMPROBANTE,
    pedido_id: Annotated[uuid.UUID | None, Form()] = None,
) -> ComprobanteSalida:
    """Foto reducida en el celular (≤ 3,5 MB). Devuelve la URL firmada para verla."""
    contenido = await archivo.read()
    return await service.subir_comprobante(
        sesion, quien, pedido_id, tipo, contenido, archivo.content_type or ""
    )


@router.get("/pedidos/{pedido_id}/comprobantes", response_model=list[ComprobanteSalida])
async def comprobantes_de_pedido(
    pedido_id: uuid.UUID, sesion: Sesion, quien: Operativo
) -> list[ComprobanteSalida]:
    return await service.comprobantes_de_pedido(sesion, quien, pedido_id)


@router.get("/comprobantes", response_model=list[ComprobanteSalida])
async def comprobantes_del_dia(
    fecha: date, sesion: Sesion, quien: Equipo, usuario_id: uuid.UUID | None = None
) -> list[ComprobanteSalida]:
    """Para conciliar: las fotos del día, por persona."""
    return await service.comprobantes_del_dia(sesion, quien, fecha, usuario_id)


@router.get("/archivos/{clave:path}", include_in_schema=False)
async def descargar_archivo(clave: str, vence: int, firma: str) -> Response:
    """Sirve un archivo del storage local con URL firmada. En S3 esto lo hace el bucket."""
    if not firma_valida(clave, vence, firma):
        return Response(status_code=status.HTTP_403_FORBIDDEN)
    leido = await storage().leer(clave)
    if leido is None:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    contenido, tipo = leido
    return Response(content=contenido, media_type=tipo)


@router.post("/pagos", response_model=PagoSalida, status_code=status.HTTP_201_CREATED)
async def registrar_pago(datos: PagoEntrada, sesion: Sesion, quien: Equipo) -> PagoSalida:
    return await service.registrar_pago(sesion, quien, datos)


@router.get("/pagos/{pago_id}", response_model=PagoSalida)
async def pago(pago_id: uuid.UUID, sesion: Sesion, quien: Equipo) -> PagoSalida:
    return await service.pago_por_id(sesion, quien, pago_id)


@router.get("/clientes/{cliente_id}/extracto", response_model=ExtractoSalida, tags=["clientes"])
async def extracto(cliente_id: uuid.UUID, sesion: Sesion, quien: Equipo) -> ExtractoSalida:
    return await service.extracto_de(sesion, quien, cliente_id)


@router.post("/clientes/{cliente_id}/ajustes", response_model=ExtractoSalida, tags=["clientes"])
async def ajuste_manual(
    cliente_id: uuid.UUID, datos: AjusteEntrada, sesion: Sesion, quien: SoloAdmin
) -> ExtractoSalida:
    return await service.ajuste_manual(sesion, quien, cliente_id, datos)


@router.get("/cobranzas/cuentas", response_model=list[CuentaACobrar])
async def cuentas_a_cobrar(sesion: Sesion, quien: Equipo) -> list[CuentaACobrar]:
    """Mis cuentas a cobrar: clientes con saldo, ordenados por zona."""
    return await service.cuentas_a_cobrar(sesion, quien)


@router.get("/caja", response_model=ResumenCaja)
async def resumen_caja(
    fecha: date,
    sesion: Sesion,
    quien: Equipo,
    usuario_id: Annotated[uuid.UUID | None, Query()] = None,
) -> ResumenCaja:
    return await service.resumen_caja(sesion, quien, fecha, usuario_id)


@router.get("/caja/rendicion", response_model=list[ResumenCaja])
async def rendicion_del_dia(fecha: date, sesion: Sesion, quien: SoloAdmin) -> list[ResumenCaja]:
    """Rendición del día: una caja por cobrador o preventista que cobró."""
    return await service.rendicion_del_dia(sesion, quien, fecha)


@router.post("/caja/cierres", response_model=CierreSalida, status_code=status.HTTP_201_CREATED)
async def cerrar_caja(datos: CierreEntrada, sesion: Sesion, quien: Equipo) -> CierreSalida:
    return await service.cerrar(sesion, quien, datos)


@router.get("/caja/cierres", response_model=list[CierreSalida])
async def cierres_del_dia(fecha: date, sesion: Sesion, quien: SoloAdmin) -> list[CierreSalida]:
    return await service.cierres_del_dia(sesion, quien, fecha)
