import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import get_settings

_hasher = PasswordHasher()


class Rol(StrEnum):
    ADMIN = "admin"
    PREVENTISTA = "preventista"
    COBRADOR = "cobrador"
    CLIENTE = "cliente"


def hashear_clave(clave: str) -> str:
    return _hasher.hash(clave)


def verificar_clave(clave: str, clave_hash: str) -> bool:
    try:
        return _hasher.verify(clave_hash, clave)
    except VerifyMismatchError:
        return False


@dataclass(frozen=True)
class Identidad:
    """Lo que viaja en el token de acceso. El filtrado por rol se hace en el servidor con esto."""

    usuario_id: uuid.UUID
    sucursal_id: uuid.UUID
    rol: Rol
    nombre: str


class TokenInvalido(Exception):
    pass


def _emitir(carga: dict[str, object], minutos: int) -> str:
    ahora = datetime.now(UTC)
    settings = get_settings()
    return jwt.encode(
        {**carga, "iat": ahora, "exp": ahora + timedelta(minutes=minutos)},
        settings.jwt_secret,
        algorithm="HS256",
    )


def emitir_acceso(identidad: Identidad) -> str:
    return _emitir(
        {
            "sub": str(identidad.usuario_id),
            "suc": str(identidad.sucursal_id),
            "rol": identidad.rol.value,
            "nom": identidad.nombre,
            "tipo": "acceso",
        },
        get_settings().jwt_acceso_minutos,
    )


def emitir_refresh(usuario_id: uuid.UUID, jti: uuid.UUID) -> str:
    return _emitir(
        {"sub": str(usuario_id), "jti": str(jti), "tipo": "refresh"},
        get_settings().jwt_refresh_dias * 24 * 60,
    )


def _decodificar(token: str, tipo: str) -> dict[str, str]:
    try:
        carga: dict[str, str] = jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError as error:
        raise TokenInvalido(str(error)) from error
    if carga.get("tipo") != tipo:
        raise TokenInvalido(f"Se esperaba un token de {tipo}")
    return carga


def leer_acceso(token: str) -> Identidad:
    carga = _decodificar(token, "acceso")
    try:
        return Identidad(
            usuario_id=uuid.UUID(carga["sub"]),
            sucursal_id=uuid.UUID(carga["suc"]),
            rol=Rol(carga["rol"]),
            nombre=carga["nom"],
        )
    except (KeyError, ValueError) as error:
        raise TokenInvalido("Token de acceso incompleto") from error


def leer_refresh(token: str) -> tuple[uuid.UUID, uuid.UUID]:
    carga = _decodificar(token, "refresh")
    try:
        return uuid.UUID(carga["sub"]), uuid.UUID(carga["jti"])
    except (KeyError, ValueError) as error:
        raise TokenInvalido("Token de refresh incompleto") from error
