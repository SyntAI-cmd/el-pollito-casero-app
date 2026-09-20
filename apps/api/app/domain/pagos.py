"""Cobros: medios presenciales, cobro mixto, comprobantes y aplicación de pagos a cuenta."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from app.domain.dinero import CERO, a_importe
from app.domain.errores import ErrorDominio

IMPORTE_MAXIMO = Decimal("100000000")


class Medio(StrEnum):
    EFECTIVO = "efectivo"
    TRANSFERENCIA = "transferencia"
    CHEQUE = "cheque"


# Transferencia y cheque no se ven en la mano: exigen la foto del comprobante.
MEDIOS_CON_COMPROBANTE = frozenset({Medio.TRANSFERENCIA, Medio.CHEQUE})


@dataclass(frozen=True)
class ParteCobro:
    medio: Medio
    importe: Decimal
    comprobante_id: str | None = None


def validar_cobro(partes: Sequence[ParteCobro], total_a_cobrar: Decimal) -> Decimal:
    """Un cobro puede ser mixto: varias partes por medio distinto que suman exactamente el total."""
    if not partes:
        raise ErrorDominio("El cobro necesita al menos una parte")
    suma = CERO
    for parte in partes:
        importe = a_importe(parte.importe)
        if importe <= CERO or importe > IMPORTE_MAXIMO:
            raise ErrorDominio(f"Importe inválido en {parte.medio}: {importe}")
        if parte.medio in MEDIOS_CON_COMPROBANTE and not parte.comprobante_id:
            raise ErrorDominio(f"El cobro por {parte.medio} necesita la foto del comprobante")
        suma += importe
    total_a_cobrar = a_importe(total_a_cobrar)
    if suma != total_a_cobrar:
        raise ErrorDominio(f"Las partes suman {suma} y el total a cobrar es {total_a_cobrar}")
    return suma


def validar_cierre_entrega(cantidad_fotos: int) -> None:
    """Una entrega no se cierra sin al menos una foto: comprobante o remito firmado."""
    if cantidad_fotos < 1:
        raise ErrorDominio("Sacá una foto del comprobante o del remito firmado antes de cerrar")


@dataclass(frozen=True)
class PedidoPendiente:
    id: str
    total: Decimal
    creado: datetime


@dataclass(frozen=True)
class Aplicacion:
    cubiertos: tuple[str, ...]
    saldo_a_favor: Decimal


def aplicar_pago(
    pendientes: Sequence[PedidoPendiente],
    importe: Decimal,
    saldo_a_favor_previo: Decimal = CERO,
) -> Aplicacion:
    """
    Un pago a cuenta cubre pedidos enteros del más viejo al más nuevo (así el remito de cada uno
    queda pagado o no, sin medias tintas). Lo que no alcanza para el siguiente queda como saldo a
    favor y se descuenta del próximo pago o pedido.
    """
    importe = a_importe(importe)
    if importe <= CERO or importe > IMPORTE_MAXIMO:
        raise ErrorDominio(f"Importe de pago inválido: {importe}")
    saldo_a_favor_previo = a_importe(saldo_a_favor_previo)
    if saldo_a_favor_previo < CERO:
        raise ErrorDominio("El saldo a favor previo no puede ser negativo")

    disponible = importe + saldo_a_favor_previo
    cubiertos: list[str] = []
    for pedido in sorted(pendientes, key=lambda p: (p.creado, p.id)):
        total = a_importe(pedido.total)
        if total > disponible:
            break
        disponible -= total
        cubiertos.append(pedido.id)
    return Aplicacion(cubiertos=tuple(cubiertos), saldo_a_favor=disponible)
