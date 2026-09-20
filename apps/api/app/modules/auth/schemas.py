import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.core.seguridad import Rol


class LoginEntrada(BaseModel):
    usuario: str = Field(min_length=2, max_length=40)
    clave: str = Field(min_length=4, max_length=200)


class RefreshEntrada(BaseModel):
    refresh: str


class UsuarioSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sucursal_id: uuid.UUID
    nombre: str
    usuario: str
    telefono: str | None
    cuit: str | None
    rol: Rol
    activo: bool


class TokensSalida(BaseModel):
    acceso: str
    refresh: str
    usuario: UsuarioSalida


class UsuarioEntrada(BaseModel):
    sucursal_id: uuid.UUID
    nombre: str = Field(min_length=2, max_length=100)
    usuario: str = Field(min_length=2, max_length=40, pattern=r"^[a-z0-9._-]+$")
    clave: str = Field(min_length=6, max_length=200)
    rol: Rol
    telefono: str | None = Field(default=None, max_length=20)
    cuit: str | None = Field(default=None, max_length=13)


class UsuarioCambios(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=100)
    clave: str | None = Field(default=None, min_length=6, max_length=200)
    rol: Rol | None = None
    telefono: str | None = Field(default=None, max_length=20)
    cuit: str | None = Field(default=None, max_length=13)
    activo: bool | None = None
    sucursal_id: uuid.UUID | None = None


class TokenPushEntrada(BaseModel):
    token: str = Field(min_length=10, max_length=200)
    plataforma: str = Field(default="", max_length=20)
