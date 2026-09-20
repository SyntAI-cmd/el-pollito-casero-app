import uuid
from datetime import date

from fastapi import APIRouter, status

from app.core.db import Sesion
from app.core.dependencias import Operativo
from app.modules.documentos import service
from app.modules.documentos.schemas import DocumentoEntrada, DocumentoSalida

router = APIRouter(prefix="/documentos", tags=["documentos"])


@router.post("", response_model=DocumentoSalida, status_code=status.HTTP_202_ACCEPTED)
async def solicitar(datos: DocumentoEntrada, sesion: Sesion, quien: Operativo) -> DocumentoSalida:
    """Encola la generación. Consultar `GET /documentos/{id}` hasta que `estado` sea `listo`."""
    return await service.solicitar(sesion, quien, datos)


@router.get("", response_model=list[DocumentoSalida])
async def listar(fecha: date, sesion: Sesion, quien: Operativo) -> list[DocumentoSalida]:
    return await service.listar(sesion, quien, fecha)


@router.get("/{documento_id}", response_model=DocumentoSalida)
async def obtener(documento_id: uuid.UUID, sesion: Sesion, quien: Operativo) -> DocumentoSalida:
    return await service.obtener(sesion, quien, documento_id)
