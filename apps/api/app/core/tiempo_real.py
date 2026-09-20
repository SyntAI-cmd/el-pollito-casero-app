"""
Tiempo real por WebSocket (React Native no trae EventSource). Un canal por sucursal; cada evento
lleva los roles que pueden verlo. Difusor en memoria: alcanza para un proceso; con varios
workers se reemplaza por Redis pub/sub sin tocar los módulos que publican.
"""

import asyncio
import json
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from fastapi import WebSocket

from app.core.seguridad import Identidad, Rol
from app.core.tiempo import ahora

TODOS = frozenset(Rol)


@dataclass
class _Conexion:
    socket: WebSocket
    identidad: Identidad


@dataclass
class Difusor:
    _por_sucursal: dict[uuid.UUID, list[_Conexion]] = field(
        default_factory=lambda: defaultdict(list)
    )

    async def conectar(self, socket: WebSocket, identidad: Identidad) -> None:
        await socket.accept()
        self._por_sucursal[identidad.sucursal_id].append(_Conexion(socket, identidad))

    def desconectar(self, socket: WebSocket, identidad: Identidad) -> None:
        conexiones = self._por_sucursal.get(identidad.sucursal_id, [])
        self._por_sucursal[identidad.sucursal_id] = [
            c for c in conexiones if c.socket is not socket
        ]

    def conectados(self, sucursal_id: uuid.UUID) -> int:
        return len(self._por_sucursal.get(sucursal_id, []))

    async def publicar(
        self,
        sucursal_id: uuid.UUID,
        tipo: str,
        datos: dict[str, Any],
        roles: frozenset[Rol] = TODOS,
        solo_usuarios: set[uuid.UUID] | None = None,
    ) -> None:
        """Manda a los conectados de la sucursal con rol permitido. Un socket caído se descarta."""
        mensaje = json.dumps({"tipo": tipo, "datos": datos, "en": ahora().isoformat()}, default=str)
        destinatarios = [
            c
            for c in list(self._por_sucursal.get(sucursal_id, []))
            if c.identidad.rol in roles
            and (solo_usuarios is None or c.identidad.usuario_id in solo_usuarios)
        ]
        resultados = await asyncio.gather(
            *(c.socket.send_text(mensaje) for c in destinatarios), return_exceptions=True
        )
        for conexion, resultado in zip(destinatarios, resultados, strict=True):
            if isinstance(resultado, Exception):
                self.desconectar(conexion.socket, conexion.identidad)


difusor = Difusor()
