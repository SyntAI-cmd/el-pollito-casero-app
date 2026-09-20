import json
import uuid

import pytest

from app.core.seguridad import Identidad, Rol, emitir_acceso
from app.core.tiempo_real import Difusor


class SocketFalso:
    def __init__(self, falla: bool = False) -> None:
        self.mensajes: list[dict[str, object]] = []
        self.falla = falla

    async def accept(self) -> None:
        pass

    async def send_text(self, texto: str) -> None:
        if self.falla:
            raise RuntimeError("socket caído")
        self.mensajes.append(json.loads(texto))


def identidad(rol: Rol, sucursal: uuid.UUID) -> Identidad:
    return Identidad(uuid.uuid4(), sucursal, rol, rol.value)


async def test_difusor_filtra_por_sucursal_rol_y_usuario() -> None:
    difusor = Difusor()
    casa, otra = uuid.uuid4(), uuid.uuid4()
    admin, preventista, cobrador = SocketFalso(), SocketFalso(), SocketFalso()
    ajeno, caido = SocketFalso(), SocketFalso(falla=True)
    id_preventista = identidad(Rol.PREVENTISTA, casa)
    await difusor.conectar(admin, identidad(Rol.ADMIN, casa))  # type: ignore[arg-type]
    await difusor.conectar(preventista, id_preventista)  # type: ignore[arg-type]
    await difusor.conectar(cobrador, identidad(Rol.COBRADOR, casa))  # type: ignore[arg-type]
    await difusor.conectar(ajeno, identidad(Rol.ADMIN, otra))  # type: ignore[arg-type]
    await difusor.conectar(caido, identidad(Rol.ADMIN, casa))  # type: ignore[arg-type]

    await difusor.publicar(casa, "pedido.estado", {"numero": "00001"}, roles=frozenset({Rol.ADMIN}))
    await difusor.publicar(
        casa,
        "pedido.estado",
        {"numero": "00001"},
        roles=frozenset({Rol.PREVENTISTA}),
        solo_usuarios={id_preventista.usuario_id},
    )
    await difusor.publicar(casa, "noticia", {"titulo": "Hola"})

    assert [m["tipo"] for m in admin.mensajes] == ["pedido.estado", "noticia"]
    assert [m["tipo"] for m in preventista.mensajes] == ["pedido.estado", "noticia"]
    assert [m["tipo"] for m in cobrador.mensajes] == ["noticia"]
    assert ajeno.mensajes == []
    # El socket que falló se descartó en el primer envío.
    assert difusor.conectados(casa) == 3


def test_websocket_exige_token_valido() -> None:
    from starlette.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect

    from app.main import app

    with TestClient(app) as tc:
        with (
            pytest.raises(WebSocketDisconnect) as rechazo,
            tc.websocket_connect("/ws?token=basura"),
        ):
            pass
        assert rechazo.value.code == 4401
        token = emitir_acceso(identidad(Rol.ADMIN, uuid.uuid4()))
        with tc.websocket_connect(f"/ws?token={token}") as ws:
            ws.send_text("ping")
