from collections.abc import Sequence

from httpx import AsyncClient

from app.integrations.push import Notificacion, PushNulo, usar_enviador_push
from app.modules.auth.models import Usuario
from tests.conftest import pedido_base


class PushFalso:
    def __init__(self) -> None:
        self.enviados: list[tuple[list[str], Notificacion]] = []

    async def enviar(self, tokens: Sequence[str], notificacion: Notificacion) -> None:
        self.enviados.append((list(tokens), notificacion))


async def test_registrar_token_y_avisar_al_preventista_asignado(
    cliente: AsyncClient,
    como_admin: dict[str, str],
    como_preventista: dict[str, str],
    preventista: Usuario,
    cliente_con_precios: dict[str, str],
) -> None:
    falso = PushFalso()
    usar_enviador_push(falso)
    try:
        registro = await cliente.post(
            "/auth/push-token",
            json={"token": "ExponentPushToken[abc123]", "plataforma": "android"},
            headers=como_preventista,
        )
        assert registro.status_code == 204
        # Mismo token otra vez: no duplica.
        await cliente.post(
            "/auth/push-token",
            json={"token": "ExponentPushToken[abc123]"},
            headers=como_preventista,
        )

        # El preventista se carga un pedido a sí mismo: no se avisa a sí mismo.
        await cliente.post(
            "/pedidos", json=pedido_base(cliente_con_precios["id"]), headers=como_preventista
        )
        assert falso.enviados == []

        # Administración le asigna uno: llega el push con el número de remito.
        creado = await cliente.post(
            "/pedidos",
            json=pedido_base(cliente_con_precios["id"], preventista_id=str(preventista.id)),
            headers=como_admin,
        )
        assert creado.status_code == 201
        assert len(falso.enviados) == 1
        tokens, notificacion = falso.enviados[0]
        assert tokens == ["ExponentPushToken[abc123]"]
        assert notificacion.titulo == f"Pedido #{creado.json()['numero']}"
        assert notificacion.datos["pedido_id"] == creado.json()["id"]
    finally:
        usar_enviador_push(PushNulo())
