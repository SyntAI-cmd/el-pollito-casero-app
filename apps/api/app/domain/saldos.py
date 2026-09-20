"""
Cuenta corriente y envases del cliente. El extracto no es una tabla aparte: se reconstruye
siempre desde pedidos, pagos y ajustes, así el saldo actual y cualquier corte histórico salen
de la misma fuente.

Convención: cargo (+) aumenta la deuda; crédito (−) la reduce. El saldo es la suma acumulada.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from app.domain.dinero import CERO, a_importe
from app.domain.errores import ErrorDominio


class TipoMovimiento(StrEnum):
    CARGO = "cargo"  # pedido a cuenta, por el importe estimado, en la fecha de creación
    AJUSTE_PESO = "ajuste_peso"  # diferencia entre lo estimado y la balanza, al pesar
    ANULACION = "anulacion"  # pedido a cuenta cancelado: se revierte todo lo cargado
    PAGO = "pago"  # pago registrado, por su importe, en su fecha
    REINTEGRO = "reintegro"  # pedido pagado y borrado: lo cobrado vuelve como saldo a favor
    AJUSTE_MANUAL = "ajuste_manual"  # saldo inicial, arreglos, cajas contadas a mano


@dataclass(frozen=True)
class Movimiento:
    fecha: datetime
    tipo: TipoMovimiento
    importe: Decimal  # con signo: + deuda, − crédito
    referencia: str  # id de pedido, pago o ajuste
    detalle: str = ""


@dataclass(frozen=True)
class LineaExtracto:
    movimiento: Movimiento
    saldo: Decimal


def extracto(movimientos: Iterable[Movimiento]) -> list[LineaExtracto]:
    ordenados = sorted(movimientos, key=lambda m: (m.fecha, m.referencia))
    lineas: list[LineaExtracto] = []
    saldo = CERO
    for movimiento in ordenados:
        saldo += a_importe(movimiento.importe)
        lineas.append(LineaExtracto(movimiento=movimiento, saldo=saldo))
    return lineas


def saldo_actual(movimientos: Iterable[Movimiento]) -> Decimal:
    return a_importe(sum((m.importe for m in movimientos), CERO))


def saldo_al(movimientos: Iterable[Movimiento], corte: datetime) -> Decimal:
    """Saldo al inicio de un instante: suma de movimientos anteriores al corte."""
    return a_importe(sum((m.importe for m in movimientos if m.fecha < corte), CERO))


@dataclass(frozen=True)
class PedidoACuenta:
    """Lo que la cuenta corriente necesita saber de un pedido a cuenta."""

    id: str
    creado: datetime
    importe_estimado: Decimal
    importe_pesado: Decimal | None = None
    pesado_en: datetime | None = None
    cancelado_en: datetime | None = None


def movimientos_de_pedido(pedido: PedidoACuenta) -> list[Movimiento]:
    """
    El cargo se registra con el importe estimado al crear el pedido (así la deuda existe desde la
    nota del día); la balanza agrega solo la diferencia, para que el extracto cuente la historia
    real en vez de reescribirla.
    """
    movimientos = [
        Movimiento(
            pedido.creado, TipoMovimiento.CARGO, a_importe(pedido.importe_estimado), pedido.id
        )
    ]
    total = a_importe(pedido.importe_estimado)
    if pedido.importe_pesado is not None:
        if pedido.pesado_en is None:
            raise ErrorDominio(f"El pedido {pedido.id} está pesado pero no tiene fecha de pesada")
        diferencia = a_importe(pedido.importe_pesado) - total
        total += diferencia
        if diferencia != CERO:
            movimientos.append(
                Movimiento(pedido.pesado_en, TipoMovimiento.AJUSTE_PESO, diferencia, pedido.id)
            )
    if pedido.cancelado_en is not None:
        movimientos.append(
            Movimiento(pedido.cancelado_en, TipoMovimiento.ANULACION, -total, pedido.id)
        )
    return movimientos


def movimiento_de_pago(
    id_pago: str, fecha: datetime, importe: Decimal, detalle: str = ""
) -> Movimiento:
    importe = a_importe(importe)
    if importe <= CERO:
        raise ErrorDominio("Un pago debe ser mayor a cero")
    return Movimiento(fecha, TipoMovimiento.PAGO, -importe, id_pago, detalle)


def movimiento_de_reintegro(id_pedido: str, fecha: datetime, importe: Decimal) -> Movimiento:
    """Pedido pagado que se borra: lo cobrado no se devuelve en mano, queda como saldo a favor."""
    importe = a_importe(importe)
    if importe <= CERO:
        raise ErrorDominio("Un reintegro debe ser mayor a cero")
    return Movimiento(fecha, TipoMovimiento.REINTEGRO, -importe, id_pedido)


@dataclass(frozen=True)
class MovimientoEnvases:
    fecha: datetime
    dejados: int = 0
    devueltos: int = 0
    referencia: str = ""


def saldo_envases(movimientos: Sequence[MovimientoEnvases], ajuste: int = 0) -> int:
    """Cajones que el cliente adeuda: dejados − devueltos, más el ajuste contado a mano."""
    for movimiento in movimientos:
        if movimiento.dejados < 0 or movimiento.devueltos < 0:
            raise ErrorDominio("Los envases dejados y devueltos no pueden ser negativos")
    return sum(m.dejados - m.devueltos for m in movimientos) + ajuste
