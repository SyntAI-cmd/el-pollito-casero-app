import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import Usuario
from app.modules.sucursales.models import Sucursal
from tests.conftest import HOY, crear_usuario, entrar, pedido_base

LOTE = {
    "lote_id": str(uuid.uuid4()),
    "producto_codigo": "entero",
    "cajas": 3,
    "bruto_total": "65.1",
}


@pytest.fixture
async def pedido(
    cliente: AsyncClient, como_preventista: dict[str, str], cliente_con_precios: dict[str, str]
) -> dict[str, object]:
    respuesta = await cliente.post(
        "/pedidos", json=pedido_base(cliente_con_precios["id"]), headers=como_preventista
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


async def test_pesada_por_lote_resta_la_tara_y_recalcula_con_el_precio_del_cliente(
    cliente: AsyncClient, como_preventista: dict[str, str], pedido: dict[str, object]
) -> None:
    url = f"/pedidos/{pedido['id']}/cajones/lote"
    pesado = await cliente.post(url, json=LOTE, headers=como_preventista)
    assert pesado.status_code == 201, pesado.text
    cuerpo = pesado.json()
    entero = cuerpo["items"][0]
    assert entero["kg_pesados"] == "60.000"  # 65.1 − 3 × 1.7
    assert entero["importe"] == "300000.00"  # × $5.000 propio
    assert entero["cajones"] == 3 and entero["cajones_cargados"] == 0
    assert cuerpo["estado"] == "preparando"
    assert cuerpo["sin_pesar"] == ["alas"] and cuerpo["pesado_en"] is None
    assert cuerpo["total"] == "300000.00"

    # Reintento del mismo lote (offline): no duplica.
    repetido = await cliente.post(url, json=LOTE, headers=como_preventista)
    assert repetido.status_code == 201
    assert repetido.json()["items"][0]["cajones"] == 3

    cajones = await cliente.get(f"/pedidos/{pedido['id']}/cajones", headers=como_preventista)
    assert [c["neto"] for c in cajones.json()] == ["20.000"] * 3
    assert {c["tara"] for c in cajones.json()} == {"1.700"}


async def test_pesada_cajon_por_cajon_es_idempotente_por_id_y_termina_el_pesaje(
    cliente: AsyncClient, como_preventista: dict[str, str], pedido: dict[str, object]
) -> None:
    await cliente.post(f"/pedidos/{pedido['id']}/cajones/lote", json=LOTE, headers=como_preventista)
    cajon = {"id": str(uuid.uuid4()), "producto_codigo": "alas", "bruto": "14.2"}
    url = f"/pedidos/{pedido['id']}/cajones"
    primero = await cliente.post(url, json=cajon, headers=como_preventista)
    assert primero.status_code == 201, primero.text
    segundo = await cliente.post(url, json=cajon, headers=como_preventista)
    alas = segundo.json()["items"][1]
    assert alas["cajones"] == 1
    assert alas["kg_pesados"] == "12.500"
    assert alas["importe"] == "51875.00"
    assert segundo.json()["pesado_en"] is not None and segundo.json()["sin_pesar"] == []
    assert segundo.json()["total"] == "351875.00"
    assert (
        await cliente.post(
            url, json={**cajon, "id": str(uuid.uuid4()), "bruto": "1.7"}, headers=como_preventista
        )
    ).status_code == 422


async def test_anular_cajon_exige_motivo_y_descuenta(
    cliente: AsyncClient, como_preventista: dict[str, str], pedido: dict[str, object]
) -> None:
    await cliente.post(f"/pedidos/{pedido['id']}/cajones/lote", json=LOTE, headers=como_preventista)
    cajones = (
        await cliente.get(f"/pedidos/{pedido['id']}/cajones", headers=como_preventista)
    ).json()
    assert (
        await cliente.post(
            f"/cajones/{cajones[0]['id']}/anular", json={"motivo": "x"}, headers=como_preventista
        )
    ).status_code == 422
    anulado = await cliente.post(
        f"/cajones/{cajones[0]['id']}/anular",
        json={"motivo": "Caja rota"},
        headers=como_preventista,
    )
    assert anulado.status_code == 200
    assert anulado.json()["items"][0]["kg_pesados"] == "40.000"
    assert anulado.json()["items"][0]["cajones"] == 2


async def test_tara_configurable_por_sucursal(
    cliente: AsyncClient,
    como_admin: dict[str, str],
    como_preventista: dict[str, str],
    sucursal: Sucursal,
    pedido: dict[str, object],
) -> None:
    cambio = await cliente.patch(
        f"/sucursales/{sucursal.id}", json={"tara": "2"}, headers=como_admin
    )
    assert cambio.json()["tara"] == "2.000"
    pesado = await cliente.post(
        f"/pedidos/{pedido['id']}/cajones",
        json={"id": str(uuid.uuid4()), "producto_codigo": "entero", "bruto": "22"},
        headers=como_preventista,
    )
    assert pesado.json()["items"][0]["kg_pesados"] == "20.000"


@pytest.fixture
async def vehiculo(cliente: AsyncClient, como_admin: dict[str, str]) -> dict[str, str]:
    respuesta = await cliente.post(
        "/vehiculos", json={"nombre": "Toyota Hino", "patente": "a974 nr"}, headers=como_admin
    )
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["patente"] == "A974NR"
    return respuesta.json()


async def test_salida_del_dia_y_cierre_del_camion(
    cliente: AsyncClient,
    sesion: AsyncSession,
    sucursal: Sucursal,
    como_admin: dict[str, str],
    preventista: Usuario,
    como_preventista: dict[str, str],
    vehiculo: dict[str, str],
    pedido: dict[str, object],
) -> None:
    salida = await cliente.put(
        "/salidas",
        json={
            "vehiculo_id": vehiculo["id"],
            "fecha": HOY.isoformat(),
            "preventista_id": str(preventista.id),
        },
        headers=como_admin,
    )
    assert salida.status_code == 200, salida.text
    assert salida.json()["pedidos"] == 1
    assert salida.json()["faltantes"][0]["numero"] == pedido["numero"]

    # El mismo preventista no puede ir en dos vehículos el mismo día.
    otro_vehiculo = (
        await cliente.post(
            "/vehiculos", json={"nombre": "Hilux", "patente": "AC226GC"}, headers=como_admin
        )
    ).json()
    repetido = await cliente.put(
        "/salidas",
        json={
            "vehiculo_id": otro_vehiculo["id"],
            "fecha": HOY.isoformat(),
            "preventista_id": str(preventista.id),
        },
        headers=como_admin,
    )
    assert repetido.status_code == 422

    # Cerrar con faltantes sin motivo: rechazado. Con motivo: los pedidos salen.
    url = f"/salidas/{salida.json()['id']}/cerrar"
    sin_motivo = await cliente.post(url, json={}, headers=como_preventista)
    assert sin_motivo.status_code == 422 and pedido["numero"] in sin_motivo.json()["mensaje"]
    cerrada = await cliente.post(
        url, json={"motivo": "Sale sin las alas"}, headers=como_preventista
    )
    assert cerrada.status_code == 200, cerrada.text
    assert cerrada.json()["cerrada_en"] is not None and cerrada.json()["hora_salida"]
    en_camino = await cliente.get(f"/pedidos/{pedido['id']}", headers=como_preventista)
    assert en_camino.json()["estado"] == "en_camino"
    assert en_camino.json()["salida_id"] == salida.json()["id"]
    assert (await cliente.post(url, json={}, headers=como_admin)).status_code == 409

    # Ya salió: no se pesa más ni se cambia la carga.
    tarde = await cliente.post(
        f"/pedidos/{pedido['id']}/cajones/lote", json=LOTE, headers=como_preventista
    )
    assert tarde.status_code == 422

    # Otro preventista no ve esta salida.
    otro = await crear_usuario(sesion, sucursal, preventista.rol, "Maxi")
    como_otro = await entrar(cliente, otro)
    assert (
        await cliente.get(f"/salidas/{salida.json()['id']}", headers=como_otro)
    ).status_code == 404


async def test_cerrar_camion_sin_faltantes_no_pide_motivo(
    cliente: AsyncClient,
    como_admin: dict[str, str],
    como_preventista: dict[str, str],
    preventista: Usuario,
    vehiculo: dict[str, str],
    pedido: dict[str, object],
) -> None:
    await cliente.post(f"/pedidos/{pedido['id']}/cajones/lote", json=LOTE, headers=como_preventista)
    await cliente.post(
        f"/pedidos/{pedido['id']}/cajones",
        json={"id": str(uuid.uuid4()), "producto_codigo": "alas", "bruto": "14.2"},
        headers=como_preventista,
    )
    cajones = (
        await cliente.get(f"/pedidos/{pedido['id']}/cajones", headers=como_preventista)
    ).json()
    for cajon in cajones:
        cargado = await cliente.post(f"/cajones/{cajon['id']}/cargar", headers=como_preventista)
        assert cargado.status_code == 200
    assert cargado.json()["cajones_cargados"] == 4
    salida = (
        await cliente.put(
            "/salidas",
            json={
                "vehiculo_id": vehiculo["id"],
                "fecha": HOY.isoformat(),
                "preventista_id": str(preventista.id),
            },
            headers=como_admin,
        )
    ).json()
    assert salida["faltantes"] == []
    cerrada = await cliente.post(f"/salidas/{salida['id']}/cerrar", json={}, headers=como_admin)
    assert cerrada.status_code == 200, cerrada.text
    assert cerrada.json()["motivo_cierre"] is None
