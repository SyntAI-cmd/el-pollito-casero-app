from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.domain.errores import ErrorDominio
from app.domain.pagos import (
    Medio,
    ParteCobro,
    PedidoPendiente,
    aplicar_pago,
    validar_cierre_entrega,
    validar_cobro,
)


def fecha(dia: int) -> datetime:
    return datetime(2026, 9, dia, 12, tzinfo=UTC)


def test_cobro_mixto_debe_sumar_exactamente_el_total() -> None:
    partes = [
        ParteCobro(Medio.EFECTIVO, Decimal("10000")),
        ParteCobro(Medio.TRANSFERENCIA, Decimal("5500.50"), comprobante_id="f1"),
    ]
    assert validar_cobro(partes, Decimal("15500.50")) == Decimal("15500.50")
    with pytest.raises(ErrorDominio, match="suman"):
        validar_cobro(partes, Decimal("15500"))


def test_transferencia_y_cheque_exigen_comprobante() -> None:
    with pytest.raises(ErrorDominio, match="comprobante"):
        validar_cobro([ParteCobro(Medio.TRANSFERENCIA, Decimal("100"))], Decimal("100"))
    with pytest.raises(ErrorDominio, match="comprobante"):
        validar_cobro([ParteCobro(Medio.CHEQUE, Decimal("100"))], Decimal("100"))
    validar_cobro([ParteCobro(Medio.EFECTIVO, Decimal("100"))], Decimal("100"))


def test_partes_vacias_o_con_importe_cero_se_rechazan() -> None:
    with pytest.raises(ErrorDominio):
        validar_cobro([], Decimal("0"))
    with pytest.raises(ErrorDominio):
        validar_cobro([ParteCobro(Medio.EFECTIVO, Decimal("0"))], Decimal("0"))


def test_entrega_no_cierra_sin_foto() -> None:
    with pytest.raises(ErrorDominio):
        validar_cierre_entrega(0)
    validar_cierre_entrega(1)


PENDIENTES = [
    PedidoPendiente("p3", Decimal("3000"), fecha(3)),
    PedidoPendiente("p1", Decimal("1000"), fecha(1)),
    PedidoPendiente("p2", Decimal("2000"), fecha(2)),
]


def test_pago_cubre_pedidos_del_mas_viejo_al_mas_nuevo() -> None:
    aplicacion = aplicar_pago(PENDIENTES, Decimal("3500"))
    assert aplicacion.cubiertos == ("p1", "p2")
    assert aplicacion.saldo_a_favor == Decimal("500.00")


def test_saldo_a_favor_previo_se_suma_al_pago() -> None:
    aplicacion = aplicar_pago(PENDIENTES, Decimal("5500"), saldo_a_favor_previo=Decimal("500"))
    assert aplicacion.cubiertos == ("p1", "p2", "p3")
    assert aplicacion.saldo_a_favor == Decimal("0.00")


def test_pago_que_no_alcanza_para_el_mas_viejo_queda_todo_a_favor() -> None:
    aplicacion = aplicar_pago(PENDIENTES, Decimal("999.99"))
    assert aplicacion.cubiertos == ()
    assert aplicacion.saldo_a_favor == Decimal("999.99")


def test_pago_sin_pendientes_queda_a_favor() -> None:
    assert aplicar_pago([], Decimal("100")).saldo_a_favor == Decimal("100.00")


def test_importes_invalidos() -> None:
    with pytest.raises(ErrorDominio):
        aplicar_pago(PENDIENTES, Decimal("0"))
    with pytest.raises(ErrorDominio):
        aplicar_pago(PENDIENTES, Decimal("100"), saldo_a_favor_previo=Decimal("-1"))
