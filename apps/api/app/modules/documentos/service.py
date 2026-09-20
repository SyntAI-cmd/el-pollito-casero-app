import logging
import uuid
from collections.abc import Callable
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errores import NoEncontrado, SinPermiso
from app.core.seguridad import Identidad, Rol
from app.core.tiempo import ahora
from app.domain.precios import Turno
from app.integrations.storage import storage
from app.modules.auditoria.service import registrar
from app.modules.documentos import datos as datos_documentos
from app.modules.documentos import repository
from app.modules.documentos.datos import Contexto
from app.modules.documentos.models import Documento, EstadoDocumento, TipoDocumento
from app.modules.documentos.render import consolidado, hojas, remitos, tickets
from app.modules.documentos.schemas import DocumentoEntrada, DocumentoSalida
from app.workers.cola import encolar

log = logging.getLogger(__name__)

RENDERERS: dict[TipoDocumento, tuple[Callable[[Contexto], bytes], str, str]] = {
    TipoDocumento.REMITOS: (remitos.render, "application/pdf", "pdf"),
    TipoDocumento.HOJA_PEDIDOS: (hojas.render_hoja_pedidos, "application/pdf", "pdf"),
    TipoDocumento.HOJA_RUTA: (hojas.render_hoja_ruta, "application/pdf", "pdf"),
    TipoDocumento.TICKETS: (tickets.render, "application/pdf", "pdf"),
    TipoDocumento.CONSOLIDADO: (
        consolidado.render,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "xlsx",
    ),
}


def _a_salida(documento: Documento) -> DocumentoSalida:
    return DocumentoSalida(
        id=documento.id,
        tipo=documento.tipo,
        estado=documento.estado,
        nombre_archivo=documento.nombre_archivo,
        url=storage().url_firmada(documento.clave_storage, minutos=120)
        if documento.clave_storage and documento.estado is EstadoDocumento.LISTO
        else None,
        error=documento.error,
        parametros=documento.parametros,
        creado_en=documento.creado_en,
        listo_en=documento.listo_en,
    )


async def solicitar(
    sesion: AsyncSession, quien: Identidad, datos: DocumentoEntrada
) -> DocumentoSalida:
    """Crea el registro y encola la generación; la app consulta hasta que esté listo."""
    if quien.rol is Rol.COBRADOR:
        raise SinPermiso("El cobrador no imprime documentos de reparto")
    if quien.rol is Rol.PREVENTISTA and datos.preventista_id not in (None, quien.usuario_id):
        raise SinPermiso("Un preventista imprime solo lo suyo")
    preventista_id = datos.preventista_id
    if quien.rol is Rol.PREVENTISTA:
        preventista_id = quien.usuario_id
    _, _, extension = RENDERERS[datos.tipo]
    fecha = datos.fecha.isoformat() if datos.fecha else "pedidos"
    documento = Documento(
        sucursal_id=datos.sucursal_id or quien.sucursal_id,
        tipo=datos.tipo,
        parametros={
            "fecha": datos.fecha.isoformat() if datos.fecha else None,
            "turno": datos.turno,
            "preventista_id": str(preventista_id) if preventista_id else None,
            "pedido_ids": [str(x) for x in datos.pedido_ids],
            "formato": datos.formato,
            # Los permisos del que pidió el documento se aplican al armar los datos en el worker.
            "quien": {
                "usuario_id": str(quien.usuario_id),
                "sucursal_id": str(quien.sucursal_id),
                "rol": quien.rol,
                "nombre": quien.nombre,
            },
        },
        nombre_archivo=f"{datos.tipo}-{fecha}.{extension}",
        creado_por=quien.usuario_id,
        creado_en=ahora(),
    )
    sesion.add(documento)
    await sesion.flush()
    registrar(sesion, quien, "documento.solicitar", "documento", documento.id, {"tipo": datos.tipo})
    await sesion.commit()
    await encolar("generar_documento", str(documento.id))
    return _a_salida(documento)


async def generar(sesion: AsyncSession, documento_id: uuid.UUID) -> None:
    """Corre en el worker. Cualquier error queda en el registro, nunca se pierde en un log."""
    documento = await repository.por_id(sesion, documento_id)
    if documento is None:
        return
    try:
        parametros = documento.parametros
        quien_datos = parametros["quien"]
        quien = Identidad(
            usuario_id=uuid.UUID(quien_datos["usuario_id"]),
            sucursal_id=uuid.UUID(quien_datos["sucursal_id"]),
            rol=Rol(quien_datos["rol"]),
            nombre=quien_datos["nombre"],
        )
        contexto = await datos_documentos.armar(
            sesion,
            quien,
            date.fromisoformat(parametros["fecha"]) if parametros.get("fecha") else None,
            Turno(parametros["turno"]) if parametros.get("turno") else None,
            uuid.UUID(parametros["preventista_id"]) if parametros.get("preventista_id") else None,
            [uuid.UUID(x) for x in parametros.get("pedido_ids", [])],
            formato=str(parametros.get("formato") or "a4"),
        )
        renderer, tipo_mime, _ = RENDERERS[documento.tipo]
        contenido = renderer(contexto)
        clave = (
            f"documentos/{documento.creado_en:%Y/%m/%d}/{documento.id}-{documento.nombre_archivo}"
        )
        await storage().guardar(clave, contenido, tipo_mime)
        documento.clave_storage = clave
        documento.estado = EstadoDocumento.LISTO
        documento.listo_en = ahora()
    except Exception as error:  # noqa: BLE001 - se informa al usuario, no se relanza
        log.exception("No se pudo generar el documento %s", documento_id)
        documento.estado = EstadoDocumento.ERROR
        documento.error = str(error)[:300]
    await sesion.commit()


async def obtener(
    sesion: AsyncSession, quien: Identidad, documento_id: uuid.UUID
) -> DocumentoSalida:
    documento = await repository.por_id(sesion, documento_id)
    if documento is None or (
        quien.rol is not Rol.ADMIN and documento.creado_por != quien.usuario_id
    ):
        raise NoEncontrado("Documento")
    return _a_salida(documento)


async def listar(sesion: AsyncSession, quien: Identidad, fecha: date) -> list[DocumentoSalida]:
    filas = await repository.del_dia(
        sesion, fecha, None if quien.rol is Rol.ADMIN else quien.usuario_id
    )
    return [_a_salida(d) for d in filas]
