"""
Tests de integración contra una base real. Por defecto SQLite en un archivo temporal (sin
Docker); con DATABASE_URL_TEST apuntando a Postgres corren igual (así lo hace CI).
"""

import os
import uuid
from collections.abc import AsyncIterator
from datetime import date
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

import app.core.db as db
import app.core.modelos  # noqa: F401  (registra todas las tablas en Base.metadata)
from app.core.db import Base, get_sesion
from app.core.seguridad import Rol, hashear_clave
from app.main import app
from app.modules.auth.models import Usuario
from app.modules.catalogo.models import Producto
from app.modules.sucursales.models import Sucursal
from scripts.semillas import PRODUCTOS


@pytest.fixture(scope="session")
def url_base_test(tmp_path_factory: pytest.TempPathFactory) -> str:
    configurada = os.environ.get("DATABASE_URL_TEST")
    if configurada:
        return configurada
    archivo: Path = tmp_path_factory.mktemp("db") / "test.sqlite"
    return f"sqlite+aiosqlite:///{archivo.as_posix()}"


@pytest.fixture(scope="session")
async def motor(url_base_test: str) -> AsyncIterator[AsyncEngine]:
    # Sin pool: el motor vive toda la sesión pero cada test corre en su propio event loop, y una
    # conexión asyncpg abierta en un loop no se puede reutilizar en otro.
    motor = create_async_engine(url_base_test, poolclass=NullPool)
    async with motor.begin() as conexion:
        if motor.dialect.name == "sqlite":
            await conexion.execute(text("PRAGMA foreign_keys=ON"))
        await conexion.run_sync(Base.metadata.drop_all)
        await conexion.run_sync(Base.metadata.create_all)
    # Las tareas del worker (modo inline) abren su propia sesión: que apunte a esta base.
    db._fabrica = async_sessionmaker(motor, expire_on_commit=False)
    yield motor
    db._fabrica = None
    await motor.dispose()


@pytest.fixture
async def sesion(motor: AsyncEngine) -> AsyncIterator[AsyncSession]:
    fabrica = async_sessionmaker(motor, expire_on_commit=False)
    async with fabrica() as sesion:
        yield sesion
    # Base limpia entre tests: se vacían todas las tablas en orden inverso de dependencias.
    async with motor.begin() as conexion:
        for tabla in reversed(Base.metadata.sorted_tables):
            await conexion.execute(tabla.delete())


@pytest.fixture
async def cliente(sesion: AsyncSession, motor: AsyncEngine) -> AsyncIterator[AsyncClient]:
    fabrica = async_sessionmaker(motor, expire_on_commit=False)

    async def _sesion_de_test() -> AsyncIterator[AsyncSession]:
        async with fabrica() as s:
            yield s

    app.dependency_overrides[get_sesion] = _sesion_de_test
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def sucursal(sesion: AsyncSession) -> Sucursal:
    fila = Sucursal(nombre="Casa central", direccion="Carril Norte s/n, El Ramblón")
    sesion.add(fila)
    await sesion.commit()
    return fila


@pytest.fixture
async def productos(sesion: AsyncSession) -> list[Producto]:
    filas = [
        Producto(codigo=codigo, nombre=nombre, descripcion=descripcion, orden=orden)
        for orden, (codigo, nombre, descripcion) in enumerate(PRODUCTOS, start=1)
    ]
    sesion.add_all(filas)
    await sesion.commit()
    return filas


async def crear_usuario(
    sesion: AsyncSession, sucursal: Sucursal, rol: Rol, nombre: str | None = None
) -> Usuario:
    usuario = Usuario(
        sucursal_id=sucursal.id,
        nombre=nombre or rol.value.title(),
        usuario=f"{rol.value}-{uuid.uuid4().hex[:6]}",
        clave_hash=hashear_clave("clave123"),
        rol=rol,
    )
    sesion.add(usuario)
    await sesion.commit()
    return usuario


async def entrar(cliente: AsyncClient, usuario: Usuario) -> dict[str, str]:
    respuesta = await cliente.post(
        "/auth/login", json={"usuario": usuario.usuario, "clave": "clave123"}
    )
    assert respuesta.status_code == 200, respuesta.text
    return {"Authorization": f"Bearer {respuesta.json()['acceso']}"}


@pytest.fixture
async def admin(sesion: AsyncSession, sucursal: Sucursal) -> Usuario:
    return await crear_usuario(sesion, sucursal, Rol.ADMIN, "Mauro")


@pytest.fixture
async def preventista(sesion: AsyncSession, sucursal: Sucursal) -> Usuario:
    return await crear_usuario(sesion, sucursal, Rol.PREVENTISTA, "Franco")


@pytest.fixture
async def cobrador(sesion: AsyncSession, sucursal: Sucursal) -> Usuario:
    return await crear_usuario(sesion, sucursal, Rol.COBRADOR, "Carlos")


@pytest.fixture
async def como_admin(cliente: AsyncClient, admin: Usuario) -> dict[str, str]:
    return await entrar(cliente, admin)


@pytest.fixture
async def como_preventista(cliente: AsyncClient, preventista: Usuario) -> dict[str, str]:
    return await entrar(cliente, preventista)


@pytest.fixture
async def como_cobrador(cliente: AsyncClient, cobrador: Usuario) -> dict[str, str]:
    return await entrar(cliente, cobrador)


HOY = date(2026, 9, 21)


@pytest.fixture
async def cliente_con_precios(
    cliente: AsyncClient,
    como_admin: dict[str, str],
    sucursal: Sucursal,
    productos: list[Producto],
) -> dict[str, str]:
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
    ficha = await cliente.post(
        "/clientes",
        json={"razon_social": "Don Pepe", "direccion": "San Martín 123", "localidad": "San Martín"},
        headers=como_admin,
    )
    await cliente.put(
        f"/clientes/{ficha.json()['id']}/precios",
        json={"precios": [{"producto_codigo": "entero", "precio": "5000"}]},
        headers=como_admin,
    )
    return ficha.json()


def pedido_base(cliente_id: str, **extra: object) -> dict[str, object]:
    return {
        "cliente_id": cliente_id,
        "fecha_reparto": HOY.isoformat(),
        "turno": "manana",
        "a_cuenta": True,
        "items": [
            {"producto_codigo": "entero", "cajas": 3},
            {"producto_codigo": "alas", "kg": "12.5"},
        ],
        **extra,
    }
