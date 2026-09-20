import uuid

from fastapi import APIRouter, status

from app.core.db import Sesion
from app.core.dependencias import Equipo, SoloAdmin
from app.modules.comunicacion import service
from app.modules.comunicacion.schemas import (
    MensajeEntrada,
    MensajeSalida,
    NoticiaCambios,
    NoticiaEntrada,
    NoticiaSalida,
)

router = APIRouter(tags=["comunicacion"])


@router.get("/noticias", response_model=list[NoticiaSalida])
async def listar_noticias(
    sesion: Sesion, quien: Equipo, incluir_archivadas: bool = False
) -> list[NoticiaSalida]:
    return await service.listar_noticias(sesion, quien, incluir_archivadas)


@router.post("/noticias", response_model=NoticiaSalida, status_code=status.HTTP_201_CREATED)
async def publicar_noticia(
    datos: NoticiaEntrada, sesion: Sesion, quien: SoloAdmin
) -> NoticiaSalida:
    return await service.publicar_noticia(sesion, quien, datos)


@router.patch("/noticias/{noticia_id}", response_model=NoticiaSalida)
async def modificar_noticia(
    noticia_id: uuid.UUID, cambios: NoticiaCambios, sesion: Sesion, quien: SoloAdmin
) -> NoticiaSalida:
    return await service.modificar_noticia(sesion, quien, noticia_id, cambios)


@router.get("/mensajes", response_model=list[MensajeSalida])
async def listar_mensajes(sesion: Sesion, quien: Equipo, limite: int = 100) -> list[MensajeSalida]:
    return await service.listar_mensajes(sesion, quien, min(max(limite, 1), 500))


@router.post("/mensajes", response_model=MensajeSalida, status_code=status.HTTP_201_CREATED)
async def enviar_mensaje(datos: MensajeEntrada, sesion: Sesion, quien: Equipo) -> MensajeSalida:
    return await service.enviar_mensaje(sesion, quien, datos)
