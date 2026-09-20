import uuid
from decimal import Decimal
from pathlib import Path

import pytest
from httpx import AsyncClient

from app.core.tiempo import hoy
from app.integrations.storage import StorageLocal, usar_storage
from app.modules.auth.models import Usuario
from tests.conftest import pedido_base


def lote() -> dict[str, object]:
    # lote_id nuevo cada vez: el mismo id no duplica cajones (idempotencia).
    return {
        "lote_id": str(uuid.uuid4()),
        "producto_codigo": "entero",
        "cajas": 3,
        "bruto_total": "65.1",
    }


FOTO = b"\xff\xd8\xff\xe0" + b"0" * 100  # cabecera JPEG + relleno


@pytest.fixture(autouse=True)
def storage_temporal(tmp_path: Path) -> None:
    usar_storage(StorageLocal(tmp_path / "archivos"))


async def pedido_pesado(
    cliente: AsyncClient, headers: dict[str, str], cliente_id: str, **extra: object
) -> dict[str, object]:
    datos = pedido_base(cliente_id, **extra)
    datos["items"] = [{"producto_codigo": "entero", "cajas": 3}]
    pedido = (await cliente.post("/pedidos", json=datos, headers=headers)).json()
    pesado = await cliente.post(
        f"/pedidos/{pedido['id']}/cajones/lote", json=lote(), headers=headers
    )
    assert pesado.json()["total"] == "300000.00"  # 60 kg × $5.000 propio
    return pesado.json()


async def subir_foto(cliente: AsyncClient, headers: dict[str, str], pedido_id: str | None) -> str:
    datos = {"tipo": "comprobante"}
    if pedido_id:
        datos["pedido_id"] = pedido_id
    respuesta = await cliente.post(
        "/comprobantes",
        data=datos,
        files={"archivo": ("recibo.jpg", FOTO, "image/jpeg")},
        headers=headers,
    )
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["url"].startswith("http://localhost:8000/archivos/")
    return respuesta.json()["id"]


async def test_cobro_mixto_en_la_entrega_con_foto_y_cierre_con_foto(
    cliente: AsyncClient, como_preventista: dict[str, str], cliente_con_precios: dict[str, str]
) -> None:
    pedido = await pedido_pesado(
        cliente, como_preventista, cliente_con_precios["id"], a_cuenta=False
    )
    # Sin foto no se cierra la entrega.
    await cliente.post(
        f"/pedidos/{pedido['id']}/estado", json={"estado": "preparando"}, headers=como_preventista
    )
    await cliente.post(
        f"/pedidos/{pedido['id']}/estado", json={"estado": "en_camino"}, headers=como_preventista
    )
    sin_foto = await cliente.post(
        f"/pedidos/{pedido['id']}/estado", json={"estado": "entregado"}, headers=como_preventista
    )
    assert sin_foto.status_code == 422 and "foto" in sin_foto.json()["mensaje"]

    # Transferencia sin comprobante: rechazada. Con foto: cobro mixto que suma el total.
    base = {
        "idempotencia": str(uuid.uuid4()),
        "cliente_id": cliente_con_precios["id"],
        "pedido_id": pedido["id"],
    }
    sin_comprobante = await cliente.post(
        "/pagos",
        json={**base, "partes": [{"medio": "transferencia", "importe": "300000"}]},
        headers=como_preventista,
    )
    assert sin_comprobante.status_code == 422
    foto = await subir_foto(cliente, como_preventista, pedido["id"])
    no_suma = await cliente.post(
        "/pagos",
        json={**base, "partes": [{"medio": "efectivo", "importe": "100000"}]},
        headers=como_preventista,
    )
    assert no_suma.status_code == 422 and "suman" in no_suma.json()["mensaje"]
    cobro = await cliente.post(
        "/pagos",
        json={
            **base,
            "partes": [
                {"medio": "efectivo", "importe": "100000"},
                {"medio": "transferencia", "importe": "200000", "comprobante_id": foto},
            ],
        },
        headers=como_preventista,
    )
    assert cobro.status_code == 201, cobro.text
    assert cobro.json()["total"] == "300000.00"
    assert cobro.json()["pedidos_cubiertos"] == [pedido["numero"]]

    # Reintento offline con la misma idempotencia: mismo pago, no se duplica.
    repetido = await cliente.post(
        "/pagos",
        json={**base, "partes": [{"medio": "efectivo", "importe": "300000"}]},
        headers=como_preventista,
    )
    assert repetido.status_code == 201 and repetido.json()["id"] == cobro.json()["id"]
    otra_vez = await cliente.post(
        "/pagos",
        json={
            **base,
            "idempotencia": str(uuid.uuid4()),
            "partes": [{"medio": "efectivo", "importe": "300000"}],
        },
        headers=como_preventista,
    )
    assert otra_vez.status_code == 409

    entregado = await cliente.post(
        f"/pedidos/{pedido['id']}/estado", json={"estado": "entregado"}, headers=como_preventista
    )
    assert entregado.status_code == 200 and entregado.json()["pagado"] is True
    fotos = await cliente.get(f"/pedidos/{pedido['id']}/comprobantes", headers=como_preventista)
    assert [f["pago_id"] for f in fotos.json()] == [cobro.json()["id"]]


async def test_pago_a_cuenta_cubre_el_mas_viejo_y_deja_saldo_a_favor(
    cliente: AsyncClient,
    como_admin: dict[str, str],
    como_preventista: dict[str, str],
    cliente_con_precios: dict[str, str],
) -> None:
    primero = await pedido_pesado(cliente, como_preventista, cliente_con_precios["id"])
    segundo = await pedido_pesado(cliente, como_preventista, cliente_con_precios["id"])
    url = f"/clientes/{cliente_con_precios['id']}/extracto"
    antes = (await cliente.get(url, headers=como_admin)).json()
    assert antes["saldo"] == "600000.00" and antes["pedidos_pendientes"] == 2
    assert [x["tipo"] for x in antes["lineas"]] == ["cargo", "ajuste_peso", "cargo", "ajuste_peso"]

    pago = await cliente.post(
        "/pagos",
        json={
            "idempotencia": str(uuid.uuid4()),
            "cliente_id": cliente_con_precios["id"],
            "partes": [{"medio": "efectivo", "importe": "350000"}],
        },
        headers=como_preventista,
    )
    assert pago.status_code == 201, pago.text
    assert pago.json()["pedidos_cubiertos"] == [primero["numero"]]
    despues = (await cliente.get(url, headers=como_admin)).json()
    assert despues["saldo"] == "250000.00" and despues["pedidos_pendientes"] == 1
    assert (await cliente.get(f"/pedidos/{primero['id']}", headers=como_admin)).json()[
        "pagado"
    ] is True
    assert (await cliente.get(f"/pedidos/{segundo['id']}", headers=como_admin)).json()[
        "pagado"
    ] is False

    # Un segundo pago que junta el sobrante cubre el segundo y deja saldo a favor.
    await cliente.post(
        "/pagos",
        json={
            "idempotencia": str(uuid.uuid4()),
            "cliente_id": cliente_con_precios["id"],
            "partes": [{"medio": "efectivo", "importe": "300000"}],
        },
        headers=como_preventista,
    )
    final = (await cliente.get(url, headers=como_admin)).json()
    assert final["saldo"] == "-50000.00" and final["saldo_a_favor"] == "50000.00"
    assert final["pedidos_pendientes"] == 0

    # El saldo a favor se descuenta del próximo pedido cobrado en la entrega.
    tercero = await pedido_pesado(
        cliente, como_preventista, cliente_con_precios["id"], a_cuenta=False
    )
    cobro = await cliente.post(
        "/pagos",
        json={
            "idempotencia": str(uuid.uuid4()),
            "cliente_id": cliente_con_precios["id"],
            "pedido_id": tercero["id"],
            "partes": [{"medio": "efectivo", "importe": "250000"}],
        },
        headers=como_preventista,
    )
    assert cobro.status_code == 201, cobro.text
    assert cobro.json()["saldo_a_favor_usado"] == "50000.00"
    assert (await cliente.get(url, headers=como_admin)).json()["saldo_a_favor"] == "0.00"

    # Ajuste manual solo para administración.
    ajuste = {"importe": "-1000", "motivo": "Arreglo por caja rota"}
    assert (
        await cliente.post(
            f"/clientes/{cliente_con_precios['id']}/ajustes", json=ajuste, headers=como_preventista
        )
    ).status_code == 403
    ajustado = await cliente.post(
        f"/clientes/{cliente_con_precios['id']}/ajustes", json=ajuste, headers=como_admin
    )
    assert ajustado.json()["saldo_a_favor"] == "1000.00"


async def test_cobrador_ve_sus_cuentas_cobra_y_cierra_su_caja(
    cliente: AsyncClient,
    como_admin: dict[str, str],
    como_preventista: dict[str, str],
    como_cobrador: dict[str, str],
    cobrador: Usuario,
    cliente_con_precios: dict[str, str],
) -> None:
    await pedido_pesado(cliente, como_preventista, cliente_con_precios["id"])
    assert (await cliente.get("/cobranzas/cuentas", headers=como_cobrador)).json() == []
    await cliente.patch(
        f"/clientes/{cliente_con_precios['id']}",
        json={"cobrador_id": str(cobrador.id)},
        headers=como_admin,
    )
    cuentas = (await cliente.get("/cobranzas/cuentas", headers=como_cobrador)).json()
    assert len(cuentas) == 1 and cuentas[0]["saldo"] == "300000.00"
    assert cuentas[0]["pedidos_pendientes"] == 1

    # El cobrador no ve pedidos ni pesa.
    assert (await cliente.get("/pedidos", headers=como_cobrador)).status_code == 403

    foto = await subir_foto(cliente, como_cobrador, None)
    cobro = await cliente.post(
        "/pagos",
        json={
            "idempotencia": str(uuid.uuid4()),
            "cliente_id": cliente_con_precios["id"],
            "partes": [
                {"medio": "efectivo", "importe": "100000"},
                {"medio": "cheque", "importe": "200000", "comprobante_id": foto},
            ],
        },
        headers=como_cobrador,
    )
    assert cobro.status_code == 201, cobro.text
    assert (await cliente.get("/cobranzas/cuentas", headers=como_cobrador)).json() == []

    caja = (
        await cliente.get("/caja", params={"fecha": hoy().isoformat()}, headers=como_cobrador)
    ).json()
    assert caja["efectivo_esperado"] == "100000.00"
    assert caja["cheques"] == "200000.00" and caja["transferencias"] == "0.00"
    assert caja["cantidad_cobros"] == 1 and caja["cierre"] is None

    no_cuadra = await cliente.post(
        "/caja/cierres",
        json={"fecha": hoy().isoformat(), "efectivo_recibido": "99000"},
        headers=como_cobrador,
    )
    assert no_cuadra.status_code == 422
    cierre = await cliente.post(
        "/caja/cierres",
        json={
            "fecha": hoy().isoformat(),
            "efectivo_recibido": "99000",
            "nota": "Faltó el vuelto de la 4",
        },
        headers=como_cobrador,
    )
    assert cierre.status_code == 201, cierre.text
    assert Decimal(cierre.json()["diferencia"]) == Decimal("-1000")
    assert (
        await cliente.post(
            "/caja/cierres",
            json={"fecha": hoy().isoformat(), "efectivo_recibido": "100000"},
            headers=como_cobrador,
        )
    ).status_code == 409
    cierres = await cliente.get(
        "/caja/cierres", params={"fecha": hoy().isoformat()}, headers=como_admin
    )
    assert [c["usuario_id"] for c in cierres.json()] == [str(cobrador.id)]
    # El cobrador no cierra la caja de otro.
    ajena = await cliente.post(
        "/caja/cierres",
        json={
            "usuario_id": str(uuid.uuid4()),
            "fecha": hoy().isoformat(),
            "efectivo_recibido": "0",
        },
        headers=como_cobrador,
    )
    assert ajena.status_code == 403


async def test_archivo_firmado_y_firma_vencida(
    cliente: AsyncClient, como_preventista: dict[str, str]
) -> None:
    foto = await subir_foto(cliente, como_preventista, None)
    fotos = await cliente.get(
        "/comprobantes", params={"fecha": hoy().isoformat()}, headers=como_preventista
    )
    urls = [f["url"] for f in fotos.json() if f["id"] == foto]
    assert urls
    if urls:
        descarga = await cliente.get(urls[0].replace("http://localhost:8000", ""))
        assert descarga.status_code == 200 and descarga.content == FOTO
        assert (
            await cliente.get(
                urls[0].replace("http://localhost:8000", "").replace("firma=", "firma=x")
            )
        ).status_code == 403


async def test_pago_parcial_no_cubre_un_pedido_sin_pesar(
    cliente: AsyncClient,
    como_admin: dict[str, str],
    como_preventista: dict[str, str],
    cliente_con_precios: dict[str, str],
) -> None:
    # Pedido a cuenta sin pesar: vale su estimado (12,5 kg de alas × $4.150 = $51.875).
    datos = pedido_base(cliente_con_precios["id"])
    datos["items"] = [{"producto_codigo": "alas", "kg": "12.5"}]
    pedido = (await cliente.post("/pedidos", json=datos, headers=como_preventista)).json()
    assert pedido["estimado"] == "51875.00" and pedido["total"] == "0.00"
    pago = await cliente.post(
        "/pagos",
        json={
            "idempotencia": str(uuid.uuid4()),
            "cliente_id": cliente_con_precios["id"],
            "partes": [{"medio": "efectivo", "importe": "30000"}],
        },
        headers=como_preventista,
    )
    assert pago.json()["pedidos_cubiertos"] == []
    extracto = (
        await cliente.get(f"/clientes/{cliente_con_precios['id']}/extracto", headers=como_admin)
    ).json()
    assert extracto["saldo"] == "21875.00" and extracto["pedidos_pendientes"] == 1
