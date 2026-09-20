import uuid

from fastapi import APIRouter, status

from app.core.db import Sesion
from app.core.dependencias import Actual, SoloAdmin
from app.modules.auth import service
from app.modules.auth.schemas import (
    LoginEntrada,
    RefreshEntrada,
    TokensSalida,
    UsuarioCambios,
    UsuarioEntrada,
    UsuarioSalida,
)

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=TokensSalida)
async def login(datos: LoginEntrada, sesion: Sesion) -> TokensSalida:
    acceso, refresh, usuario = await service.login(sesion, datos.usuario, datos.clave)
    return TokensSalida(
        acceso=acceso, refresh=refresh, usuario=UsuarioSalida.model_validate(usuario)
    )


@router.post("/auth/refresh", response_model=TokensSalida)
async def refrescar(datos: RefreshEntrada, sesion: Sesion) -> TokensSalida:
    acceso, refresh, usuario = await service.refrescar(sesion, datos.refresh)
    return TokensSalida(
        acceso=acceso, refresh=refresh, usuario=UsuarioSalida.model_validate(usuario)
    )


@router.post("/auth/salir", status_code=status.HTTP_204_NO_CONTENT)
async def salir(datos: RefreshEntrada, sesion: Sesion) -> None:
    await service.cerrar_sesion(sesion, datos.refresh)


@router.get("/auth/yo", response_model=UsuarioSalida)
async def yo(sesion: Sesion, identidad: Actual) -> UsuarioSalida:
    return UsuarioSalida.model_validate(await service.yo(sesion, identidad))


@router.get("/usuarios", response_model=list[UsuarioSalida], tags=["equipo"])
async def listar_usuarios(sesion: Sesion, quien: SoloAdmin) -> list[UsuarioSalida]:
    return [UsuarioSalida.model_validate(u) for u in await service.listar_usuarios(sesion, quien)]


@router.post(
    "/usuarios", response_model=UsuarioSalida, status_code=status.HTTP_201_CREATED, tags=["equipo"]
)
async def crear_usuario(datos: UsuarioEntrada, sesion: Sesion, quien: SoloAdmin) -> UsuarioSalida:
    return UsuarioSalida.model_validate(await service.crear_usuario(sesion, quien, datos))


@router.patch("/usuarios/{usuario_id}", response_model=UsuarioSalida, tags=["equipo"])
async def modificar_usuario(
    usuario_id: uuid.UUID, cambios: UsuarioCambios, sesion: Sesion, quien: SoloAdmin
) -> UsuarioSalida:
    return UsuarioSalida.model_validate(
        await service.modificar_usuario(sesion, quien, usuario_id, cambios)
    )
