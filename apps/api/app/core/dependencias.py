from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.errores import SinPermiso
from app.core.seguridad import Identidad, Rol, TokenInvalido, leer_acceso

_bearer = HTTPBearer(auto_error=False)


async def identidad_actual(
    credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Identidad:
    if credenciales is None:
        raise TokenInvalido("Falta el token de acceso")
    return leer_acceso(credenciales.credentials)


Actual = Annotated[Identidad, Depends(identidad_actual)]


def requiere_rol(*roles: Rol) -> Callable[..., Coroutine[Any, Any, Identidad]]:
    """Corta en el router; el filtrado fino (qué pedidos ve un preventista) lo hace cada service."""

    async def _verificar(request: Request, identidad: Actual) -> Identidad:
        if identidad.rol not in roles:
            raise SinPermiso(f"Esta operación es para {', '.join(roles)}")
        return identidad

    return _verificar


SoloAdmin = Annotated[Identidad, Depends(requiere_rol(Rol.ADMIN))]
Equipo = Annotated[Identidad, Depends(requiere_rol(Rol.ADMIN, Rol.PREVENTISTA, Rol.COBRADOR))]
Operativo = Annotated[Identidad, Depends(requiere_rol(Rol.ADMIN, Rol.PREVENTISTA))]
