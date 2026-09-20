import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator

from app.domain.precios import Turno
from app.modules.documentos.models import EstadoDocumento, TipoDocumento


class DocumentoEntrada(BaseModel):
    tipo: TipoDocumento
    fecha: date | None = None
    turno: Turno | None = None
    preventista_id: uuid.UUID | None = None
    pedido_ids: list[uuid.UUID] = Field(default_factory=list, max_length=200)
    sucursal_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _alcance(self) -> "DocumentoEntrada":
        if self.fecha is None and not self.pedido_ids:
            raise ValueError("Indicá la fecha o los pedidos")
        return self


class DocumentoSalida(BaseModel):
    id: uuid.UUID
    tipo: TipoDocumento
    estado: EstadoDocumento
    nombre_archivo: str
    url: str | None
    error: str | None
    parametros: dict[str, object]
    creado_en: datetime
    listo_en: datetime | None
