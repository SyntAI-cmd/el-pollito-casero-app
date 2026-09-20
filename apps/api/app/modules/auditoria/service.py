import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.seguridad import Identidad
from app.modules.auditoria.models import AuditLog


def registrar(
    sesion: AsyncSession,
    quien: Identidad | None,
    accion: str,
    entidad: str,
    entidad_id: uuid.UUID | str,
    detalle: dict[str, Any] | None = None,
) -> AuditLog:
    """Se agrega a la sesión abierta: viaja en la misma transacción que la operación auditada."""
    fila = AuditLog(
        sucursal_id=quien.sucursal_id if quien else None,
        usuario_id=quien.usuario_id if quien else None,
        accion=accion,
        entidad=entidad,
        entidad_id=str(entidad_id),
        detalle=detalle or {},
    )
    sesion.add(fila)
    return fila
