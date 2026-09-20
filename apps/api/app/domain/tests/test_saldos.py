from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.domain.errores import ErrorDominio
from app.domain.saldos import (
    MovimientoEnvases,
    PedidoACuenta,
    TipoMovimiento,
    extracto,
    movimiento_de_pago,
    movimiento_de_reintegro,
    movimientos_de_pedido,
    saldo_actual,
    saldo_al,
    saldo_envases,
)


def fecha(dia: int, hora: int = 15) -> datetime:
    return datetime(2026, 9, dia, hora, tzinfo=UTC)


def test_extracto_cargo_ajuste_por_peso_anulacion_reintegro_y_pago() -> None:
    """Mismo caso que validaba el sistema anterior: los saldos tienen que cuadrar igual."""
    movimientos = [
        *movimientos_de_pedido(
            PedidoACuenta(
                "PC-1",
                creado=fecha(1),
                importe_estimado=Decimal("10000"),
                importe_pesado=Decimal("12000"),
                pesado_en=fecha(2),
            )
        ),
        *movimientos_de_pedido(
            PedidoACuenta(
                "PC-2", creado=fecha(3), importe_estimado=Decimal("5000"), cancelado_en=fecha(4)
            )
        ),
        movimiento_de_reintegro("PC-3", fecha(5), Decimal("3000")),
        movimiento_de_pago("PG-1", fecha(6), Decimal("7000"), "efectivo · Franco"),
    ]
    lineas = extracto(movimientos)
    assert [(x.movimiento.tipo, x.movimiento.importe, x.saldo) for x in lineas] == [
        (TipoMovimiento.CARGO, Decimal("10000.00"), Decimal("10000.00")),
        (TipoMovimiento.AJUSTE_PESO, Decimal("2000.00"), Decimal("12000.00")),
        (TipoMovimiento.CARGO, Decimal("5000.00"), Decimal("17000.00")),
        (TipoMovimiento.ANULACION, Decimal("-5000.00"), Decimal("12000.00")),
        (TipoMovimiento.REINTEGRO, Decimal("-3000.00"), Decimal("9000.00")),
        (TipoMovimiento.PAGO, Decimal("-7000.00"), Decimal("2000.00")),
    ]
    assert saldo_actual(movimientos) == Decimal("2000.00")
    assert saldo_al(movimientos, fecha(4, 0)) == Decimal("17000.00")
    assert saldo_al(movimientos, fecha(30)) == Decimal("2000.00")
    assert saldo_al(movimientos, fecha(1, 0)) == Decimal("0.00")


def test_pedido_pesado_igual_al_estimado_no_genera_ajuste() -> None:
    movimientos = movimientos_de_pedido(
        PedidoACuenta(
            "p", fecha(1), Decimal("100"), importe_pesado=Decimal("100"), pesado_en=fecha(2)
        )
    )
    assert [m.tipo for m in movimientos] == [TipoMovimiento.CARGO]


def test_anulacion_revierte_cargo_y_ajuste_juntos() -> None:
    movimientos = movimientos_de_pedido(
        PedidoACuenta(
            "p",
            fecha(1),
            Decimal("100"),
            importe_pesado=Decimal("90"),
            pesado_en=fecha(2),
            cancelado_en=fecha(3),
        )
    )
    assert movimientos[-1].importe == Decimal("-90.00")
    assert saldo_actual(movimientos) == Decimal("0.00")


def test_pedido_pesado_sin_fecha_es_un_error() -> None:
    with pytest.raises(ErrorDominio):
        movimientos_de_pedido(
            PedidoACuenta("p", fecha(1), Decimal("1"), importe_pesado=Decimal("1"))
        )


def test_pagos_y_reintegros_deben_ser_positivos() -> None:
    with pytest.raises(ErrorDominio):
        movimiento_de_pago("x", fecha(1), Decimal("0"))
    with pytest.raises(ErrorDominio):
        movimiento_de_reintegro("x", fecha(1), Decimal("-5"))


def test_envases_dejados_menos_devueltos_mas_ajuste() -> None:
    movimientos = [
        MovimientoEnvases(fecha(1), dejados=5),
        MovimientoEnvases(fecha(2), devueltos=1),
        MovimientoEnvases(fecha(3), dejados=2, devueltos=2),
    ]
    assert saldo_envases(movimientos) == 4
    assert saldo_envases(movimientos, ajuste=-2) == 2
    with pytest.raises(ErrorDominio):
        saldo_envases([MovimientoEnvases(fecha(1), dejados=-1)])
