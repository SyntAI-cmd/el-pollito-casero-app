"""GeocodificadorGoogle: acota a Mendoza y no rompe nada si Google no responde."""

from decimal import Decimal

import httpx
import pytest

from app.integrations.maps import GeocodificadorGoogle


def _respuesta(lat: float, lng: float, precision: str = "ROOFTOP", status: str = "OK") -> dict:
    return {
        "status": status,
        "results": [
            {"geometry": {"location": {"lat": lat, "lng": lng}, "location_type": precision}}
        ],
    }


async def _geocodificar_con(respuesta: object, monkeypatch: pytest.MonkeyPatch) -> object:
    capturado: dict[str, object] = {}

    def manejar(peticion: httpx.Request) -> httpx.Response:
        capturado["params"] = dict(peticion.url.params)
        if isinstance(respuesta, Exception):
            raise respuesta
        return httpx.Response(200, json=respuesta)

    transporte = httpx.MockTransport(manejar)
    original = httpx.AsyncClient

    def cliente_falso(**kwargs: object) -> httpx.AsyncClient:
        kwargs.pop("transport", None)
        return original(transport=transporte, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(httpx, "AsyncClient", cliente_falso)
    resultado = await GeocodificadorGoogle("clave").geocodificar("San Martín 123", "San Martín")
    return resultado, capturado


async def test_devuelve_coordenadas_dentro_de_mendoza(monkeypatch: pytest.MonkeyPatch) -> None:
    respuesta = _respuesta(-33.0812347, -68.4691234)
    resultado, capturado = await _geocodificar_con(respuesta, monkeypatch)
    assert resultado is not None
    assert (resultado.lat, resultado.lng) == (Decimal("-33.081235"), Decimal("-68.469123"))
    params = capturado["params"]
    assert params["address"] == "San Martín 123, San Martín, Mendoza"
    assert params["components"] == "country:AR"
    assert "bounds" in params and "key" in params


async def test_descarta_resultados_fuera_del_rectangulo(monkeypatch: pytest.MonkeyPatch) -> None:
    # San Martín, Buenos Aires: Google lo encuentra, nosotros no lo aceptamos.
    resultado, _ = await _geocodificar_con(_respuesta(-34.57, -58.53), monkeypatch)
    assert resultado is None


async def test_descarta_precision_aproximada(monkeypatch: pytest.MonkeyPatch) -> None:
    resultado, _ = await _geocodificar_con(_respuesta(-33.08, -68.47, "APPROXIMATE"), monkeypatch)
    assert resultado is None


async def test_sin_resultados_o_sin_red_devuelve_none(monkeypatch: pytest.MonkeyPatch) -> None:
    resultado, _ = await _geocodificar_con({"status": "ZERO_RESULTS", "results": []}, monkeypatch)
    assert resultado is None
    resultado, _ = await _geocodificar_con(httpx.ConnectError("sin red"), monkeypatch)
    assert resultado is None


async def test_direccion_vacia_no_consulta() -> None:
    assert await GeocodificadorGoogle("clave").geocodificar("  ", "San Martín") is None
