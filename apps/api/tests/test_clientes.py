from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.maps import Coordenadas, GeocodificadorNulo, usar_geocodificador
from app.modules.auth.models import Usuario
from app.modules.catalogo.models import Producto
from app.modules.sucursales.models import Sucursal
from tests.conftest import crear_usuario, entrar

FICHA = {
    "razon_social": "Carnicería Don Pepe",
    "nombre_comercial": "Don Pepe",
    "cuit": "20-12345678-9",
    "telefono": "0263 15 555-1234",
    "direccion": "San Martín 123",
    "localidad": "San Martín",
    "lista": "mayorista",
    "turno": "manana",
}


async def test_alta_normaliza_el_telefono_y_calcula_el_estado_de_ficha(
    cliente: AsyncClient, como_admin: dict[str, str]
) -> None:
    creado = await cliente.post("/clientes", json=FICHA, headers=como_admin)
    assert creado.status_code == 201, creado.text
    ficha = creado.json()
    assert ficha["telefono"] == "5492635551234"
    assert ficha["estado_ficha"] == "revisar"  # sin coordenadas todavía

    sin_cuit = await cliente.post(
        "/clientes", json={**FICHA, "cuit": None, "telefono": None}, headers=como_admin
    )
    assert sin_cuit.json()["estado_ficha"] == "sin_cuit"

    mismo_telefono = await cliente.post("/clientes", json=FICHA, headers=como_admin)
    assert mismo_telefono.status_code == 409
    telefono_invalido = await cliente.post(
        "/clientes", json={**FICHA, "telefono": "1234"}, headers=como_admin
    )
    assert telefono_invalido.status_code == 422


async def test_geocoding_completa_la_ficha_cuando_hay_proveedor(
    cliente: AsyncClient, como_admin: dict[str, str]
) -> None:
    class Falso:
        async def geocodificar(self, direccion: str, localidad: str) -> Coordenadas:
            return Coordenadas(Decimal("-33.081"), Decimal("-68.469"))

    usar_geocodificador(Falso())
    try:
        creado = await cliente.post("/clientes", json=FICHA, headers=como_admin)
    finally:
        usar_geocodificador(GeocodificadorNulo())
    assert Decimal(creado.json()["lat"]) == Decimal("-33.081")
    assert creado.json()["estado_ficha"] == "completa"


async def test_preventista_ve_solo_sus_clientes_y_los_sin_asignar(
    cliente: AsyncClient,
    sesion: AsyncSession,
    sucursal: Sucursal,
    como_admin: dict[str, str],
    preventista: Usuario,
    como_preventista: dict[str, str],
) -> None:
    otro = await crear_usuario(sesion, sucursal, preventista.rol, "Maxi")
    como_otro = await entrar(cliente, otro)

    mio = await cliente.post(
        "/clientes",
        json={**FICHA, "telefono": None, "nombre_comercial": "Mío"},
        headers=como_preventista,
    )
    assert mio.json()["preventista_id"] == str(preventista.id)
    de_otro = await cliente.post(
        "/clientes",
        json={**FICHA, "telefono": None, "nombre_comercial": "De otro"},
        headers=como_otro,
    )
    libre = await cliente.post(
        "/clientes",
        json={**FICHA, "telefono": None, "nombre_comercial": "Libre"},
        headers=como_admin,
    )

    visibles = await cliente.get("/clientes", headers=como_preventista)
    assert {c["nombre_comercial"] for c in visibles.json()} == {"Mío", "Libre"}
    assert (
        await cliente.get(f"/clientes/{de_otro.json()['id']}", headers=como_preventista)
    ).status_code == 404
    assert (
        await cliente.get(f"/clientes/{libre.json()['id']}", headers=como_preventista)
    ).status_code == 200
    todos = await cliente.get("/clientes", headers=como_admin)
    assert len(todos.json()) == 3

    # El preventista no toca lo que es de administración.
    veto = await cliente.patch(
        f"/clientes/{mio.json()['id']}",
        json={"credito_habilitado": False},
        headers=como_preventista,
    )
    assert veto.status_code == 403
    busqueda = await cliente.get("/clientes", params={"q": "libre"}, headers=como_admin)
    assert [c["nombre_comercial"] for c in busqueda.json()] == ["Libre"]


async def test_cobrador_ve_solo_las_cuentas_asignadas(
    cliente: AsyncClient,
    como_admin: dict[str, str],
    como_cobrador: dict[str, str],
    cobrador: Usuario,
) -> None:
    asignado = await cliente.post(
        "/clientes",
        json={**FICHA, "telefono": None, "cobrador_id": str(cobrador.id)},
        headers=como_admin,
    )
    await cliente.post("/clientes", json={**FICHA, "telefono": None}, headers=como_admin)
    visibles = await cliente.get("/clientes", headers=como_cobrador)
    assert [c["id"] for c in visibles.json()] == [asignado.json()["id"]]
    assert (await cliente.post("/clientes", json=FICHA, headers=como_cobrador)).status_code == 403


@pytest.fixture
async def con_listas(
    cliente: AsyncClient, como_admin: dict[str, str], sucursal: Sucursal, productos: list[Producto]
) -> None:
    await cliente.put(
        "/precios/listas",
        json={
            "sucursal_id": str(sucursal.id),
            "precios": [
                {
                    "producto_codigo": "entero",
                    "lista": "mayorista",
                    "turno": "manana",
                    "precio": "5500",
                },
                {
                    "producto_codigo": "alas",
                    "lista": "mayorista",
                    "turno": "manana",
                    "precio": "4150",
                },
            ],
        },
        headers=como_admin,
    )


async def test_precio_propio_pisa_la_lista_y_lo_que_falta_queda_sin_precio(
    cliente: AsyncClient,
    como_admin: dict[str, str],
    como_preventista: dict[str, str],
    con_listas: None,
) -> None:
    ficha = (await cliente.post("/clientes", json=FICHA, headers=como_admin)).json()
    precios = (
        await cliente.get(f"/clientes/{ficha['id']}/precios", headers=como_preventista)
    ).json()
    por_codigo = {p["producto_codigo"]: p for p in precios}
    assert por_codigo["entero"] == {
        "producto_codigo": "entero",
        "producto_nombre": "Pollo entero",
        "precio": "5500.00",
        "origen": "lista",
    }
    assert por_codigo["suprema"]["precio"] is None
    assert por_codigo["suprema"]["origen"] == "sin_precio"

    # Cualquiera del equipo con acceso al cliente le guarda un precio propio.
    guardado = await cliente.put(
        f"/clientes/{ficha['id']}/precios",
        json={"precios": [{"producto_codigo": "entero", "precio": "5000"}]},
        headers=como_preventista,
    )
    assert guardado.status_code == 200, guardado.text
    entero = next(p for p in guardado.json() if p["producto_codigo"] == "entero")
    assert entero == {**entero, "precio": "5000.00", "origen": "propio"}

    borrado = await cliente.put(
        f"/clientes/{ficha['id']}/precios",
        json={"precios": [{"producto_codigo": "entero", "precio": None}]},
        headers=como_admin,
    )
    entero = next(p for p in borrado.json() if p["producto_codigo"] == "entero")
    assert entero["origen"] == "lista" and entero["precio"] == "5500.00"


async def test_envases_dejados_devueltos_y_ajuste(
    cliente: AsyncClient, como_admin: dict[str, str], como_preventista: dict[str, str]
) -> None:
    ficha = (await cliente.post("/clientes", json=FICHA, headers=como_admin)).json()
    url = f"/clientes/{ficha['id']}/envases"
    assert (
        await cliente.post(url, json={"dejados": 0, "devueltos": 0}, headers=como_admin)
    ).status_code == 422
    await cliente.post(url, json={"dejados": 5}, headers=como_preventista)
    saldo = await cliente.post(
        url, json={"devueltos": 2, "nota": "Trajo dos"}, headers=como_preventista
    )
    assert saldo.json()["saldo"] == 3
    await cliente.patch(f"/clientes/{ficha['id']}", json={"ajuste_envases": -1}, headers=como_admin)
    final = await cliente.get(url, headers=como_admin)
    assert final.json()["saldo"] == 2
    assert [m["dejados"] for m in final.json()["movimientos"]] == [5, 0]
