"""Tareas en segundo plano. Cada una abre su propia sesión: no comparte la de la petición."""

import uuid
from typing import Any

from app.core.db import fabrica_sesiones
from app.modules.documentos import service as documentos


async def generar_documento(ctx: dict[str, Any], documento_id: str) -> None:
    async with fabrica_sesiones()() as sesion:
        await documentos.generar(sesion, uuid.UUID(documento_id))
