from httpx import AsyncClient

from app.modules.catalogo.models import Producto
from app.modules.sucursales.models import Sucursal


async def test_sucursales_y_zonas(
    cliente: AsyncClient, como_admin: dict[str, str], como_preventista: dict[str, str]
) -> None:
    creada = await cliente.post(
        "/sucursales", json={"nombre": "Rivadavia", "direccion": "Ruta 7"}, headers=como_admin
    )
    assert creada.status_code == 201
    sucursal_id = creada.json()["id"]
    assert (
        await cliente.post("/sucursales", json={"nombre": "Rivadavia"}, headers=como_admin)
    ).status_code == 409

    zona = await cliente.post(
        f"/sucursales/{sucursal_id}/zonas", json={"nombre": "Norte"}, headers=como_admin
    )
    assert zona.status_code == 201
    zonas = await cliente.get(f"/sucursales/{sucursal_id}/zonas", headers=como_admin)
    assert [z["nombre"] for z in zonas.json()] == ["Norte"]

    # El preventista solo ve su sucursal; la otra le queda vedada.
    propias = await cliente.get("/sucursales", headers=como_preventista)
    assert [s["nombre"] for s in propias.json()] == ["Casa central"]
    ajena = await cliente.get(f"/sucursales/{sucursal_id}/zonas", headers=como_preventista)
    assert ajena.status_code == 403


async def test_productos_y_listas_de_precio(
    cliente: AsyncClient,
    como_admin: dict[str, str],
    como_preventista: dict[str, str],
    sucursal: Sucursal,
    productos: list[Producto],
) -> None:
    lista = await cliente.get("/productos", headers=como_preventista)
    assert [p["codigo"] for p in lista.json()][:3] == ["entero", "cuarto_trasero", "alas"]
    assert len(lista.json()) == 12  # diez cortes + suprema de muslo + "otro"

    precios = {
        "sucursal_id": str(sucursal.id),
        "precios": [
            {
                "producto_codigo": "entero",
                "lista": "mayorista",
                "turno": "manana",
                "precio": "5500",
            },
            {"producto_codigo": "entero", "lista": "mayorista", "turno": "tarde", "precio": "5600"},
        ],
    }
    assert (
        await cliente.put("/precios/listas", json=precios, headers=como_preventista)
    ).status_code == 403
    guardadas = await cliente.put("/precios/listas", json=precios, headers=como_admin)
    assert guardadas.status_code == 200, guardadas.text
    assert {(p["turno"], p["precio"]) for p in guardadas.json()} == {
        ("manana", "5500.00"),
        ("tarde", "5600.00"),
    }

    # Volver a guardar actualiza en vez de duplicar.
    precios["precios"][0]["precio"] = "5700"
    await cliente.put("/precios/listas", json=precios, headers=como_admin)
    consulta = await cliente.get(
        "/precios/listas",
        params={"sucursal_id": str(sucursal.id), "turno": "manana"},
        headers=como_preventista,
    )
    assert [p["precio"] for p in consulta.json()] == ["5700.00"]

    invalido = {**precios, "precios": [{**precios["precios"][0], "producto_codigo": "trozado"}]}
    assert (
        await cliente.put("/precios/listas", json=invalido, headers=como_admin)
    ).status_code == 422
