import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NoticiaEntrada(BaseModel):
    titulo: str = Field(min_length=2, max_length=120)
    cuerpo: str = Field(default="", max_length=2000)
    fijada: bool = False


class NoticiaCambios(BaseModel):
    titulo: str | None = Field(default=None, min_length=2, max_length=120)
    cuerpo: str | None = Field(default=None, max_length=2000)
    fijada: bool | None = None
    archivada: bool | None = None


class NoticiaSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sucursal_id: uuid.UUID
    autor_id: uuid.UUID
    titulo: str
    cuerpo: str
    fijada: bool
    archivada: bool
    creado_en: datetime


class MensajeEntrada(BaseModel):
    cuerpo: str = Field(min_length=1, max_length=1000)


class MensajeSalida(BaseModel):
    id: uuid.UUID
    autor_id: uuid.UUID
    autor_nombre: str
    cuerpo: str
    creado_en: datetime
