from decimal import Decimal

import pytest

from app.domain.cierre_caja import cerrar_caja, resumir_caja
from app.domain.errores import ErrorDominio
from app.domain.pagos import Medio, ParteCobro
from app.domain.pedidos import (
    Estado,
    PedidoParaCargar,
    faltantes_para_cerrar,
    transicionar,
    validar_cierre_camion,
    validar_preventistas_salida,
)
from app.domain.pesada import Cajon, marcar_cargado
from app.domain.remitos import formatear_numero, siguiente_numero

COBROS = [
    ParteCobro(Medio.EFECTIVO, Decimal("10000")),
    ParteCobro(Medio.EFECTIVO, Decimal("2500.50")),
    ParteCobro(Medio.TRANSFERENCIA, Decimal("8000"), comprobante_id="a"),
    ParteCobro(Medio.CHEQUE, Decimal("15000"), comprobante_id="b"),
]


def test_transferencias_y_cheques_no_suman_al_efectivo_a_rendir() -> None:
    resumen = resumir_caja(COBROS)
    assert resumen.efectivo_esperado == Decimal("12500.50")
    assert resumen.transferencias == Decimal("8000.00")
    assert resumen.cheques == Decimal("15000.00")
    assert resumen.total_cobrado == Decimal("35500.50")
    assert resumen.cantidad_cobros == 4


def test_cierre_que_cuadra_no_necesita_nota() -> None:
    cierre = cerrar_caja(resumir_caja(COBROS), Decimal("12500.50"))
    assert cierre.cuadra and cierre.diferencia == 0


def test_cierre_con_diferencia_exige_nota() -> None:
    with pytest.raises(ErrorDominio, match="no cuadra"):
        cerrar_caja(resumir_caja(COBROS), Decimal("12000"))
    cierre = cerrar_caja(
        resumir_caja(COBROS), Decimal("12000"), nota="Faltan $500, se los llevó el vuelto"
    )
    assert cierre.diferencia == Decimal("-500.50")
    with pytest.raises(ErrorDominio):
        cerrar_caja(resumir_caja(COBROS), Decimal("-1"))


def test_numeracion_de_remitos_correlativa_de_cinco_digitos() -> None:
    assert formatear_numero(12) == "00012"
    assert formatear_numero(99999) == "99999"
    assert siguiente_numero(None) == 1
    assert siguiente_numero(41) == 42
    with pytest.raises(ErrorDominio):
        formatear_numero(0)
    with pytest.raises(ErrorDominio):
        siguiente_numero(99999)


def test_transiciones_de_estado_validas_e_invalidas() -> None:
    assert transicionar(Estado.RECIBIDO, Estado.PREPARANDO) is Estado.PREPARANDO
    assert transicionar(Estado.PREPARANDO, Estado.EN_CAMINO) is Estado.EN_CAMINO
    assert transicionar(Estado.EN_CAMINO, Estado.ENTREGADO) is Estado.ENTREGADO
    assert transicionar(Estado.RECIBIDO, Estado.CANCELADO) is Estado.CANCELADO
    for actual, nuevo in [
        (Estado.ENTREGADO, Estado.CANCELADO),
        (Estado.CANCELADO, Estado.RECIBIDO),
        (Estado.RECIBIDO, Estado.ENTREGADO),
        (Estado.EN_CAMINO, Estado.PREPARANDO),
    ]:
        with pytest.raises(ErrorDominio):
            transicionar(actual, nuevo)


def test_salida_lleva_hasta_dos_preventistas_sin_repetir() -> None:
    assert validar_preventistas_salida(["ana", "ana", "juan"]) == ("ana", "juan")
    with pytest.raises(ErrorDominio):
        validar_preventistas_salida([])
    with pytest.raises(ErrorDominio):
        validar_preventistas_salida(["a", "b", "c"])


def test_cerrar_camion_detecta_lo_que_falta_pesar_y_cargar() -> None:
    cargado = marcar_cargado(Cajon("c1", "entero", Decimal("20")))
    pedidos = [
        PedidoParaCargar("p1", "00001", cajas_pedidas=2, cajones=[cargado, cargado]),
        PedidoParaCargar(
            "p2", "00002", cajas_pedidas=3, cajones=[cargado, Cajon("c2", "entero", Decimal("20"))]
        ),
    ]
    faltantes = faltantes_para_cerrar(pedidos)
    assert [(f.numero, f.sin_pesar, f.sin_cargar) for f in faltantes] == [("00002", 1, 1)]
    with pytest.raises(ErrorDominio, match="#00002"):
        validar_cierre_camion(pedidos, motivo=None)
    assert validar_cierre_camion(pedidos, motivo="El cliente canceló una caja") == faltantes
    assert validar_cierre_camion(pedidos[:1], motivo=None) == []
