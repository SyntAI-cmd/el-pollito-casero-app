from httpx import AsyncClient

from app.modules.auth.models import Usuario
from app.modules.sucursales.models import Sucursal


async def test_login_devuelve_tokens_y_el_usuario(cliente: AsyncClient, admin: Usuario) -> None:
    respuesta = await cliente.post(
        "/auth/login", json={"usuario": admin.usuario, "clave": "clave123"}
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["acceso"] and cuerpo["refresh"]
    assert cuerpo["usuario"]["rol"] == "admin"
    assert "clave_hash" not in cuerpo["usuario"]


async def test_login_con_clave_incorrecta_no_revela_si_el_usuario_existe(
    cliente: AsyncClient, admin: Usuario
) -> None:
    mala = await cliente.post("/auth/login", json={"usuario": admin.usuario, "clave": "otra1234"})
    inexistente = await cliente.post("/auth/login", json={"usuario": "nadie", "clave": "otra1234"})
    assert mala.status_code == inexistente.status_code == 401
    assert mala.json()["mensaje"] == inexistente.json()["mensaje"]


async def test_yo_requiere_token(cliente: AsyncClient, como_admin: dict[str, str]) -> None:
    assert (await cliente.get("/auth/yo")).status_code == 401
    respuesta = await cliente.get("/auth/yo", headers=como_admin)
    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == "Mauro"


async def test_refresh_rota_y_el_anterior_deja_de_servir(
    cliente: AsyncClient, admin: Usuario
) -> None:
    login = (
        await cliente.post("/auth/login", json={"usuario": admin.usuario, "clave": "clave123"})
    ).json()
    primero = await cliente.post("/auth/refresh", json={"refresh": login["refresh"]})
    assert primero.status_code == 200
    assert primero.json()["refresh"] != login["refresh"]
    repetido = await cliente.post("/auth/refresh", json={"refresh": login["refresh"]})
    assert repetido.status_code == 401


async def test_salir_revoca_el_refresh(cliente: AsyncClient, admin: Usuario) -> None:
    login = (
        await cliente.post("/auth/login", json={"usuario": admin.usuario, "clave": "clave123"})
    ).json()
    assert (
        await cliente.post("/auth/salir", json={"refresh": login["refresh"]})
    ).status_code == 204
    assert (
        await cliente.post("/auth/refresh", json={"refresh": login["refresh"]})
    ).status_code == 401


async def test_admin_administra_el_equipo_y_el_preventista_no(
    cliente: AsyncClient,
    como_admin: dict[str, str],
    como_preventista: dict[str, str],
    sucursal: Sucursal,
) -> None:
    nuevo = {
        "sucursal_id": str(sucursal.id),
        "nombre": "Nahuel Castro",
        "usuario": "nahuel",
        "clave": "secreta1",
        "rol": "preventista",
    }
    assert (
        await cliente.post("/usuarios", json=nuevo, headers=como_preventista)
    ).status_code == 403
    creado = await cliente.post("/usuarios", json=nuevo, headers=como_admin)
    assert creado.status_code == 201, creado.text
    duplicado = await cliente.post("/usuarios", json=nuevo, headers=como_admin)
    assert duplicado.status_code == 409

    baja = await cliente.patch(
        f"/usuarios/{creado.json()['id']}", json={"activo": False}, headers=como_admin
    )
    assert baja.status_code == 200 and baja.json()["activo"] is False
    entrar = await cliente.post("/auth/login", json={"usuario": "nahuel", "clave": "secreta1"})
    assert entrar.status_code == 403

    lista = await cliente.get("/usuarios", headers=como_admin)
    assert {u["usuario"] for u in lista.json()} >= {"nahuel"}
