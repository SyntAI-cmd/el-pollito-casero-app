import uuid
from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import Usuario
from app.modules.sucursales.models import Sucursal
from tests.conftest import HOY, crear_usuario, entrar, pedido_base


async def test_crear_pedido_numera_correlativo_y_resuelve_precios_en_el_servidor(
    cliente: AsyncClient, como_admin: dict[str, str], cliente_con_precios: dict[str, str]
) -> None:
    primero = await cliente.post(
        "/pedidos", json=pedido_base(cliente_con_precios["id"]), headers=como_admin
    )
    assert primero.status_code == 201, primero.text
    pedido = primero.json()
    assert pedido["numero"] == "00001"
    assert pedido["estado"] == "recibido"
    entero, alas = pedido["items"]
    assert entero["precio"] == "5000.00" and entero["precio_propio"] is True  # propio pisa lista
    assert alas["precio"] == "4150.00" and alas["precio_propio"] is False  # lista
    # Nada vale hasta pasar por la balanza; el estimado sale de los kilos pedidos.
    assert pedido["total"] == "0.00"
    assert pedido["estimado"] == "51875.00"
    assert pedido["sin_pesar"] == ["entero", "alas"]

    segundo = await cliente.post(
        "/pedidos", json=pedido_base(cliente_con_precios["id"], total="999999"), headers=como_admin
    )
    assert segundo.json()["numero"] == "00002"
    assert segundo.json()["total"] == "0.00"


async def test_precio_tipeado_en_el_pedido_puede_guardarse_como_propio(
    cliente: AsyncClient, como_admin: dict[str, str], cliente_con_precios: dict[str, str]
) -> None:
    datos = pedido_base(cliente_con_precios["id"])
    datos["items"] = [
        {
            "producto_codigo": "suprema",
            "cajas": 1,
            "precio": "11000",
            "guardar_precio_propio": True,
        },
        {"producto_codigo": "muslo", "cajas": 1},
    ]
    creado = await cliente.post("/pedidos", json=datos, headers=como_admin)
    assert creado.status_code == 201, creado.text
    assert creado.json()["sin_precio"] == ["muslo"]
    precios = await cliente.get(
        f"/clientes/{cliente_con_precios['id']}/precios", headers=como_admin
    )
    suprema = next(p for p in precios.json() if p["producto_codigo"] == "suprema")
    assert suprema == {**suprema, "precio": "11000.00", "origen": "propio"}


async def test_pedido_a_cuenta_exige_credito_habilitado(
    cliente: AsyncClient, como_admin: dict[str, str], cliente_con_precios: dict[str, str]
) -> None:
    await cliente.patch(
        f"/clientes/{cliente_con_precios['id']}",
        json={"credito_habilitado": False},
        headers=como_admin,
    )
    respuesta = await cliente.post(
        "/pedidos", json=pedido_base(cliente_con_precios["id"]), headers=como_admin
    )
    assert respuesta.status_code == 422
    assert "cuenta corriente" in respuesta.json()["mensaje"]


async def test_preventista_solo_ve_y_opera_sus_pedidos(
    cliente: AsyncClient,
    sesion: AsyncSession,
    sucursal: Sucursal,
    como_admin: dict[str, str],
    preventista: Usuario,
    como_preventista: dict[str, str],
    cliente_con_precios: dict[str, str],
) -> None:
    otro = await crear_usuario(sesion, sucursal, preventista.rol, "Maxi")
    como_otro = await entrar(cliente, otro)
    mio = await cliente.post(
        "/pedidos", json=pedido_base(cliente_con_precios["id"]), headers=como_preventista
    )
    assert mio.json()["preventista_id"] == str(preventista.id)
    ajeno = await cliente.post(
        "/pedidos", json=pedido_base(cliente_con_precios["id"]), headers=como_otro
    )
    compartido = await cliente.post(
        "/pedidos",
        json=pedido_base(
            cliente_con_precios["id"],
            preventista_id=str(otro.id),
            segundo_preventista_id=str(preventista.id),
        ),
        headers=como_admin,
    )
    lista = await cliente.get("/pedidos", headers=como_preventista)
    assert {p["numero"] for p in lista.json()} == {
        mio.json()["numero"],
        compartido.json()["numero"],
    }
    assert (
        await cliente.get(f"/pedidos/{ajeno.json()['id']}", headers=como_preventista)
    ).status_code == 404
    assert (
        await cliente.get(f"/pedidos/{compartido.json()['id']}", headers=como_preventista)
    ).status_code == 200

    a_nombre_de_otro = await cliente.post(
        "/pedidos",
        json=pedido_base(cliente_con_precios["id"], preventista_id=str(otro.id)),
        headers=como_preventista,
    )
    assert a_nombre_de_otro.status_code == 403
    assert (
        await cliente.delete(f"/pedidos/{mio.json()['id']}", headers=como_preventista)
    ).status_code == 403


async def test_estados_y_cancelacion_con_motivo(
    cliente: AsyncClient, como_admin: dict[str, str], cliente_con_precios: dict[str, str]
) -> None:
    pedido = (
        await cliente.post(
            "/pedidos", json=pedido_base(cliente_con_precios["id"]), headers=como_admin
        )
    ).json()
    url = f"/pedidos/{pedido['id']}/estado"
    assert (
        await cliente.post(url, json={"estado": "entregado"}, headers=como_admin)
    ).status_code == 422
    assert (
        await cliente.post(url, json={"estado": "cancelado"}, headers=como_admin)
    ).status_code == 422
    cancelado = await cliente.post(
        url, json={"estado": "cancelado", "motivo": "El cliente no abrió"}, headers=como_admin
    )
    assert cancelado.status_code == 200
    assert cancelado.json()["estado"] == "cancelado"
    assert cancelado.json()["motivo_cancelacion"] == "El cliente no abrió"
    eventos = await cliente.get(f"/pedidos/{pedido['id']}/eventos", headers=como_admin)
    assert [e["tipo"] for e in eventos.json()] == ["creado", "estado"]


async def test_borrar_pedido_pagado_devuelve_saldo_a_favor_y_deja_auditoria(
    cliente: AsyncClient,
    sesion: AsyncSession,
    como_admin: dict[str, str],
    cliente_con_precios: dict[str, str],
) -> None:
    pedido = (
        await cliente.post(
            "/pedidos", json=pedido_base(cliente_con_precios["id"]), headers=como_admin
        )
    ).json()
    await cliente.post(
        f"/pedidos/{pedido['id']}/cajones/lote",
        json={
            "lote_id": str(uuid.uuid4()),
            "producto_codigo": "entero",
            "cajas": 3,
            "bruto_total": "65.1",
        },
        headers=como_admin,
    )
    # Simula el cobro (el módulo de cobros llega en la Fase 5).
    from sqlalchemy import update

    from app.modules.pedidos.models import Pedido

    await sesion.execute(
        update(Pedido).where(Pedido.id == uuid.UUID(pedido["id"])).values(pagado=True)
    )
    await sesion.commit()

    assert (await cliente.delete(f"/pedidos/{pedido['id']}", headers=como_admin)).status_code == 204
    assert (await cliente.get(f"/pedidos/{pedido['id']}", headers=como_admin)).status_code == 404
    ficha = await cliente.get(f"/clientes/{cliente_con_precios['id']}", headers=como_admin)
    assert Decimal(ficha.json()["saldo_a_favor"]) == Decimal("300000.00")  # 60 kg × $5.000

    from sqlalchemy import select

    from app.modules.auditoria.models import AuditLog

    filas = (
        await sesion.scalars(select(AuditLog).where(AuditLog.accion == "pedido.eliminar"))
    ).all()
    assert len(filas) == 1 and filas[0].detalle["pedido"]["numero"] == pedido["numero"]


async def test_nota_del_dia_agrupa_por_producto_y_preventista(
    cliente: AsyncClient,
    como_admin: dict[str, str],
    como_preventista: dict[str, str],
    cliente_con_precios: dict[str, str],
) -> None:
    await cliente.post(
        "/pedidos", json=pedido_base(cliente_con_precios["id"]), headers=como_preventista
    )
    await cliente.post("/pedidos", json=pedido_base(cliente_con_precios["id"]), headers=como_admin)
    nota = await cliente.get("/pedidos/dia", params={"fecha": HOY.isoformat()}, headers=como_admin)
    assert nota.status_code == 200, nota.text
    cuerpo = nota.json()
    assert cuerpo["cantidad_pedidos"] == 2
    entero = next(t for t in cuerpo["por_producto"] if t["producto_codigo"] == "entero")
    assert entero["cajas"] == 6 and entero["pedidos"] == 2
    assert {g["preventista_nombre"] for g in cuerpo["por_preventista"]} == {"Franco", "Sin asignar"}
    # El preventista ve solo lo suyo en su nota.
    propia = await cliente.get(
        "/pedidos/dia", params={"fecha": HOY.isoformat()}, headers=como_preventista
    )
    assert propia.json()["cantidad_pedidos"] == 1
