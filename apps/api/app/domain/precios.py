"""Precios: listas por turno y zona, precio propio que pisa la lista, totales de pedido."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.domain.dinero import CERO, a_importe, importe_renglon
from app.domain.errores import ErrorDominio

PRECIO_MAXIMO = Decimal("1000000")


class Lista(StrEnum):
    MAYORISTA = "mayorista"
    INTERMEDIO = "intermedio"
    MINORISTA = "minorista"


class Turno(StrEnum):
    MANANA = "manana"
    TARDE = "tarde"


# Los diez cortes del catálogo. El precio base del negocio es el del pollo entero mayorista.
PRODUCTOS: tuple[str, ...] = (
    "entero",
    "cuarto_trasero",
    "alas",
    "pechuga",
    "suprema",
    "menudos",
    "rancho",
    "pechuga_con_alas",
    "muslo",
    "garras",
)
PRODUCTO_BASE = "entero"


def validar_precio(precio: Decimal) -> Decimal:
    precio = a_importe(precio)
    if precio <= CERO or precio > PRECIO_MAXIMO:
        raise ErrorDominio(f"Precio inválido: {precio}")
    return precio


@dataclass(frozen=True)
class PrecioLista:
    producto_id: str
    lista: Lista
    turno: Turno
    precio: Decimal
    zona_id: str | None = None  # None = precio general, vale para cualquier zona


def resolver_precio(
    producto_id: str,
    precios_cliente: Mapping[str, Decimal],
    listas: Sequence[PrecioLista],
    lista: Lista,
    turno: Turno,
    zona_id: str | None,
) -> Decimal | None:
    """
    Precio por kilo de un producto para un cliente. El precio propio pisa la lista; dentro de la
    lista, la fila de la zona pisa a la general. Sin nada, devuelve None: el renglón queda
    "sin precio" hasta que alguien lo tipea.
    """
    propio = precios_cliente.get(producto_id)
    if propio is not None:
        return validar_precio(propio)

    general: Decimal | None = None
    for fila in listas:
        if fila.producto_id != producto_id or fila.lista != lista or fila.turno != turno:
            continue
        if fila.zona_id is not None and fila.zona_id == zona_id:
            return validar_precio(fila.precio)
        if fila.zona_id is None:
            general = fila.precio
    return validar_precio(general) if general is not None else None


@dataclass(frozen=True)
class Renglon:
    """Un producto del pedido. Se pide por cajas o por kilos; se cobra por kilos pesados."""

    producto_id: str
    precio: Decimal | None
    cajas: int | None = None
    kg_pedidos: Decimal | None = None
    kg_pesados: Decimal | None = None

    @property
    def pesado(self) -> bool:
        return self.kg_pesados is not None

    @property
    def importe(self) -> Decimal:
        """Lo que vale hoy. Sin precio o sin pesar no vale nada: el importe lo pone la balanza."""
        if self.precio is None or self.kg_pesados is None:
            return CERO
        return importe_renglon(self.precio, self.kg_pesados)

    @property
    def importe_estimado(self) -> Decimal:
        """Kilos pedidos × precio: la referencia de la nota del día antes de pesar."""
        if self.precio is None:
            return CERO
        kilos = self.kg_pesados if self.kg_pesados is not None else self.kg_pedidos
        return importe_renglon(self.precio, kilos) if kilos is not None else CERO


@dataclass(frozen=True)
class Totales:
    subtotal: Decimal
    estimado: Decimal
    sin_precio: tuple[str, ...]
    sin_pesar: tuple[str, ...]

    @property
    def completo(self) -> bool:
        return not self.sin_precio and not self.sin_pesar


def validar_renglon(renglon: Renglon) -> None:
    if renglon.producto_id not in PRODUCTOS:
        raise ErrorDominio(f"Producto desconocido: {renglon.producto_id}")
    if renglon.cajas is None and renglon.kg_pedidos is None:
        raise ErrorDominio(f"Indicá cajas o kilos para {renglon.producto_id}")
    if renglon.cajas is not None and (renglon.cajas < 0 or renglon.cajas > 500):
        raise ErrorDominio(f"Las cajas de {renglon.producto_id} deben estar entre 0 y 500")
    if renglon.kg_pedidos is not None and (
        renglon.kg_pedidos <= CERO or renglon.kg_pedidos > Decimal("5000")
    ):
        raise ErrorDominio(f"Los kilos de {renglon.producto_id} deben estar entre 0 y 5000")
    if renglon.precio is not None:
        validar_precio(renglon.precio)


def totales_pedido(renglones: Sequence[Renglon]) -> Totales:
    """Los totales se calculan siempre en el servidor. La app nunca manda un total."""
    if not renglones:
        raise ErrorDominio("El pedido necesita al menos un producto")
    vistos: set[str] = set()
    for renglon in renglones:
        validar_renglon(renglon)
        if renglon.producto_id in vistos:
            raise ErrorDominio(f"Producto repetido: {renglon.producto_id}")
        vistos.add(renglon.producto_id)
    return Totales(
        subtotal=a_importe(sum((r.importe for r in renglones), CERO)),
        estimado=a_importe(sum((r.importe_estimado for r in renglones), CERO)),
        sin_precio=tuple(r.producto_id for r in renglones if r.precio is None),
        sin_pesar=tuple(r.producto_id for r in renglones if not r.pesado),
    )
