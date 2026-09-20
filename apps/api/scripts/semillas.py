"""
Semillas idempotentes: sucursal, admin, los diez cortes y las listas de precio vigentes al
14/09/2026 (docs/referencia/business.json). Correr con `uv run python -m scripts.semillas`.

Sin ADMIN_CLAVE en el entorno no crea el admin: nada de claves inventadas.

`--prueba` agrega además dos preventistas (clave EQUIPO_CLAVE), diez clientes "Prueba N" y diez
pedidos para hoy, para probar pesada, carga y reparto sin tocar datos reales.
`--borrar-prueba` los elimina.
"""

import asyncio
import os
import sys
from datetime import date
from decimal import Decimal

from sqlalchemy import select

import app.core.modelos  # noqa: F401
from app.core.db import fabrica_sesiones
from app.core.seguridad import Identidad, Rol, hashear_clave
from app.core.tiempo import hoy
from app.domain.precios import Lista, Turno
from app.modules.auth.models import Usuario
from app.modules.catalogo.models import ListaPrecio, Producto
from app.modules.clientes.models import Cliente
from app.modules.flota.models import Vehiculo
from app.modules.pedidos import service as pedidos
from app.modules.pedidos.models import Pedido
from app.modules.pedidos.schemas import ItemEntrada, PedidoEntrada
from app.modules.sucursales.models import Sucursal

PRODUCTOS: list[tuple[str, str, str]] = [
    ("entero", "Pollo entero", "Pollo entero fresco, con piel."),
    ("cuarto_trasero", "Cuarto trasero", "Pata y muslo juntos, con piel."),
    ("alas", "Alas", "Alas frescas enteras."),
    ("pechuga", "Pechuga", "Pechuga fresca con hueso y piel."),
    ("suprema", "Suprema", "Filete de pechuga sin hueso ni piel."),
    ("menudos", "Menudos", "Hígado, corazón y molleja frescos."),
    ("rancho", "Rancho", "Carcasa y espinazo para caldos."),
    ("pechuga_con_alas", "Pechuga con alas", "Pechuga entera con las alas, con piel."),
    ("muslo", "Muslo", "Muslos frescos con piel."),
    ("garras", "Garras", "Patas de pollo frescas y limpias."),
]

# (mayorista, intermedio, minorista) por kilo. Base: pollo entero mayorista $5.500.
PRECIOS: dict[str, tuple[str, str, str]] = {
    "entero": ("5500", "6000", "6500"),
    "cuarto_trasero": ("5150", "5620", "6090"),
    "alas": ("4150", "4530", "4900"),
    "pechuga": ("8280", "9030", "9790"),
    "suprema": ("11690", "12750", "13820"),
    "menudos": ("2330", "2540", "2750"),
    "rancho": ("750", "820", "890"),
    "pechuga_con_alas": ("6080", "6630", "7190"),
    "muslo": ("5940", "6480", "7020"),
    "garras": ("750", "820", "890"),
}

VEHICULOS: list[tuple[str, str, str]] = [
    ("Toyota Hino", "A974NR", "Camión"),
    ("Toyota Hilux", "AC226GC", "Camioneta nueva"),
    ("Toyota Hilux", "ENQ091", "Camioneta vieja"),
    ("Toyota Hilux", "AI014LY", "Carlos"),
]


async def sembrar() -> None:
    async with fabrica_sesiones()() as sesion:
        sucursal = await sesion.scalar(select(Sucursal).where(Sucursal.nombre == "Casa central"))
        if sucursal is None:
            sucursal = Sucursal(nombre="Casa central", direccion="Carril Norte s/n, El Ramblón")
            sesion.add(sucursal)
            await sesion.flush()

        existentes = {p.codigo: p for p in (await sesion.scalars(select(Producto))).all()}
        for orden, (codigo, nombre, descripcion) in enumerate(PRODUCTOS, start=1):
            if codigo not in existentes:
                producto = Producto(
                    codigo=codigo, nombre=nombre, descripcion=descripcion, orden=orden
                )
                sesion.add(producto)
                existentes[codigo] = producto
        await sesion.flush()

        listas = (await sesion.scalars(select(ListaPrecio))).all()
        claves = {(f.producto_id, f.lista, f.turno, f.zona_id) for f in listas}
        for codigo, precios in PRECIOS.items():
            producto = existentes[codigo]
            for lista, precio in zip(Lista, precios, strict=True):
                for turno in Turno:
                    if (producto.id, lista, turno, None) not in claves:
                        sesion.add(
                            ListaPrecio(
                                sucursal_id=sucursal.id,
                                producto_id=producto.id,
                                lista=lista,
                                turno=turno,
                                precio=Decimal(precio),
                            )
                        )

        patentes = {v.patente for v in (await sesion.scalars(select(Vehiculo))).all()}
        for nombre, patente, nota in VEHICULOS:
            if patente not in patentes:
                sesion.add(
                    Vehiculo(sucursal_id=sucursal.id, nombre=nombre, patente=patente, nota=nota)
                )

        clave = os.environ.get("ADMIN_CLAVE")
        if clave and not await sesion.scalar(select(Usuario).where(Usuario.usuario == "admin")):
            sesion.add(
                Usuario(
                    sucursal_id=sucursal.id,
                    nombre="Administración",
                    usuario="admin",
                    clave_hash=hashear_clave(clave),
                    rol=Rol.ADMIN,
                )
            )
        await sesion.commit()
    print("Semillas aplicadas.")


PREVENTISTAS_PRUEBA = [("Preventista Uno", "prueba.uno"), ("Preventista Dos", "prueba.dos")]
COBRADOR_PRUEBA = ("Cobrador Prueba", "prueba.cobra")


async def sembrar_prueba(fecha: date | None = None) -> None:
    fecha = fecha or hoy()
    clave = os.environ.get("EQUIPO_CLAVE")
    if not clave:
        raise SystemExit("Definí EQUIPO_CLAVE para crear los usuarios de prueba")
    async with fabrica_sesiones()() as sesion:
        sucursal = await sesion.scalar(select(Sucursal).where(Sucursal.nombre == "Casa central"))
        admin = await sesion.scalar(select(Usuario).where(Usuario.rol == Rol.ADMIN))
        if sucursal is None or admin is None:
            raise SystemExit("Corré primero las semillas base con ADMIN_CLAVE")
        preventistas: list[Usuario] = []
        for nombre, usuario in PREVENTISTAS_PRUEBA:
            fila = await sesion.scalar(select(Usuario).where(Usuario.usuario == usuario))
            if fila is None:
                fila = Usuario(
                    sucursal_id=sucursal.id,
                    nombre=nombre,
                    usuario=usuario,
                    clave_hash=hashear_clave(clave),
                    rol=Rol.PREVENTISTA,
                )
                sesion.add(fila)
            preventistas.append(fila)
        cobrador = await sesion.scalar(select(Usuario).where(Usuario.usuario == COBRADOR_PRUEBA[1]))
        if cobrador is None:
            cobrador = Usuario(
                sucursal_id=sucursal.id,
                nombre=COBRADOR_PRUEBA[0],
                usuario=COBRADOR_PRUEBA[1],
                clave_hash=hashear_clave(clave),
                rol=Rol.COBRADOR,
            )
            sesion.add(cobrador)
        await sesion.flush()

        clientes: list[Cliente] = []
        for n in range(1, 11):
            nombre = f"Prueba {n}"
            ficha = await sesion.scalar(select(Cliente).where(Cliente.nombre_comercial == nombre))
            if ficha is None:
                ficha = Cliente(
                    sucursal_id=sucursal.id,
                    codigo=f"PRUEBA{n:02d}",
                    razon_social=f"Comercio de prueba {n}",
                    nombre_comercial=nombre,
                    direccion=f"Calle de prueba {n * 100}",
                    localidad="San Martín",
                    preventista_id=preventistas[n % 2].id,
                    cobrador_id=cobrador.id,
                    lat=Decimal("-33.081") + Decimal(n) / 1000,
                    lng=Decimal("-68.469") - Decimal(n) / 1000,
                )
                sesion.add(ficha)
            clientes.append(ficha)
        await sesion.commit()

        quien = Identidad(admin.id, sucursal.id, Rol.ADMIN, admin.nombre)
        existentes = await sesion.scalar(
            select(Pedido).where(Pedido.fecha_reparto == fecha, Pedido.cliente_id == clientes[0].id)
        )
        if existentes is None:
            for n, cliente in enumerate(clientes, start=1):
                await pedidos.crear(
                    sesion,
                    quien,
                    PedidoEntrada(
                        cliente_id=cliente.id,
                        fecha_reparto=fecha,
                        turno=Turno.MANANA if n <= 6 else Turno.TARDE,
                        a_cuenta=n % 3 == 0,
                        preventista_id=preventistas[n % 2].id,
                        items=[
                            ItemEntrada(producto_codigo="entero", cajas=n),
                            ItemEntrada(producto_codigo="alas", kg=Decimal(5 * n)),
                        ],
                        observaciones="Pedido de prueba",
                    ),
                )
    print(f"Datos de prueba listos para {fecha}.")


async def borrar_prueba() -> None:
    async with fabrica_sesiones()() as sesion:
        filas = (await sesion.scalars(select(Cliente).where(Cliente.codigo.like("PRUEBA%")))).all()
        for cliente in filas:
            for pedido in (
                await sesion.scalars(select(Pedido).where(Pedido.cliente_id == cliente.id))
            ).all():
                await sesion.delete(pedido)
            await sesion.delete(cliente)
        for _, usuario in [*PREVENTISTAS_PRUEBA, COBRADOR_PRUEBA]:
            fila = await sesion.scalar(select(Usuario).where(Usuario.usuario == usuario))
            if fila is not None:
                fila.activo = False
        await sesion.commit()
    print("Datos de prueba borrados (los usuarios quedan dados de baja).")


if __name__ == "__main__":
    if "--borrar-prueba" in sys.argv:
        asyncio.run(borrar_prueba())
    else:
        asyncio.run(sembrar())
        if "--prueba" in sys.argv:
            asyncio.run(sembrar_prueba())
