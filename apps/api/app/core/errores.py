from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.seguridad import TokenInvalido
from app.domain.errores import ErrorDominio


class NoEncontrado(Exception):
    def __init__(self, que: str = "Recurso") -> None:
        super().__init__(f"{que} no encontrado")


class SinPermiso(Exception):
    def __init__(self, detalle: str = "No tenés permiso para esta operación") -> None:
        super().__init__(detalle)


class Conflicto(Exception):
    """Estado que no admite la operación (número duplicado, usuario inactivo, etc.)."""


def _respuesta(status: int, codigo: str, mensaje: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"codigo": codigo, "mensaje": mensaje})


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(ErrorDominio)
    async def _dominio(_: Request, error: ErrorDominio) -> JSONResponse:
        return _respuesta(422, "regla_de_negocio", str(error))

    @app.exception_handler(NoEncontrado)
    async def _no_encontrado(_: Request, error: NoEncontrado) -> JSONResponse:
        return _respuesta(404, "no_encontrado", str(error))

    @app.exception_handler(SinPermiso)
    async def _sin_permiso(_: Request, error: SinPermiso) -> JSONResponse:
        return _respuesta(403, "sin_permiso", str(error))

    @app.exception_handler(Conflicto)
    async def _conflicto(_: Request, error: Conflicto) -> JSONResponse:
        return _respuesta(409, "conflicto", str(error))

    @app.exception_handler(TokenInvalido)
    async def _token(_: Request, error: TokenInvalido) -> JSONResponse:
        return _respuesta(401, "no_autenticado", str(error))
