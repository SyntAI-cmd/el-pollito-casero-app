from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_health_responde_ok() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as cliente:
        respuesta = await cliente.get("/health")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "ok"
    assert cuerpo["version"]
