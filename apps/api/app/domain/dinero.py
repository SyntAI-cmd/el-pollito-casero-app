"""Importes y kilos como Decimal. Nunca float: la cuenta corriente pierde centavos con flotantes."""

from decimal import ROUND_HALF_UP, Decimal

CENTAVO = Decimal("0.01")
GRAMO = Decimal("0.001")
CERO = Decimal("0")

Numero = Decimal | int | str


def a_importe(valor: Numero) -> Decimal:
    return Decimal(valor).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def a_kilos(valor: Numero) -> Decimal:
    return Decimal(valor).quantize(GRAMO, rounding=ROUND_HALF_UP)


def importe_renglon(precio_por_kilo: Numero, kilos: Numero) -> Decimal:
    """Se cobra por kilo: precio × kilos, redondeado al centavo una sola vez al final."""
    return a_importe(Decimal(precio_por_kilo) * Decimal(kilos))
