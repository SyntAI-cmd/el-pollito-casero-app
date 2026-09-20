"""
Notificaciones push detrás de una interfaz. Implementación: servicio de push de Expo
(https://exp.host/--/api/v2/push/send), que no necesita credenciales para tokens de Expo Go y
builds con EAS. Cambiar de proveedor no toca ningún módulo.
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Notificacion:
    titulo: str
    cuerpo: str
    datos: dict[str, Any] = field(default_factory=dict)


class EnviadorPush(Protocol):
    async def enviar(self, tokens: Sequence[str], notificacion: Notificacion) -> None: ...


class PushNulo:
    async def enviar(self, tokens: Sequence[str], notificacion: Notificacion) -> None:
        return None


class ExpoPush:
    URL = "https://exp.host/--/api/v2/push/send"

    async def enviar(self, tokens: Sequence[str], notificacion: Notificacion) -> None:
        if not tokens:
            return
        mensajes = [
            {
                "to": token,
                "title": notificacion.titulo,
                "body": notificacion.cuerpo,
                "data": notificacion.datos,
                "sound": "default",
            }
            for token in tokens
        ]
        try:
            async with httpx.AsyncClient(timeout=10) as cliente:
                respuesta = await cliente.post(self.URL, json=mensajes)
                respuesta.raise_for_status()
        except httpx.HTTPError as error:
            # Un push perdido no puede tirar la operación que lo disparó.
            log.warning("No se pudo mandar el push: %s", error)


_enviador: EnviadorPush = ExpoPush()


def enviador_push() -> EnviadorPush:
    return _enviador


def usar_enviador_push(implementacion: EnviadorPush) -> None:
    global _enviador
    _enviador = implementacion
