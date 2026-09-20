"""WebSocket /ws?token=<acceso>. El token va en la query porque RN no manda cabeceras en WS."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.seguridad import TokenInvalido, leer_acceso
from app.core.tiempo_real import difusor

router = APIRouter()


@router.websocket("/ws")
async def canal(socket: WebSocket, token: str) -> None:
    try:
        identidad = leer_acceso(token)
    except TokenInvalido:
        await socket.close(code=4401)
        return
    await difusor.conectar(socket, identidad)
    try:
        while True:
            # El cliente solo manda "ping"; todo lo demás viaja del servidor al cliente.
            await socket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        difusor.desconectar(socket, identidad)
