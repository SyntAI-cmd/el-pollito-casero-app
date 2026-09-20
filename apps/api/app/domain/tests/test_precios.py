from decimal import Decimal

import pytest

from app.domain.dinero import importe_renglon
from app.domain.errores import ErrorDominio
from app.domain.precios import (
    Lista,
    PrecioLista,
    Renglon,
    Turno,
    resolver_precio,
    totales_pedido,
    validar_precio,
)

LISTAS = [
    PrecioLista("entero", Lista.MAYORISTA, Turno.MANANA, Decimal("5500")),
    PrecioLista("entero", Lista.MAYORISTA, Turno.MANANA, Decimal("5400"), zona_id="norte"),
    PrecioLista("entero", Lista.MAYORISTA, Turno.TARDE, Decimal("5600")),
    PrecioLista("entero", Lista.MINORISTA, Turno.MANANA, Decimal("6500")),
    PrecioLista("alas", Lista.MAYORISTA, Turno.MANANA, Decimal("4150")),
]


def test_importe_se_redondea_al_centavo_una_sola_vez() -> None:
    assert importe_renglon(Decimal("5500"), Decimal("12.345")) == Decimal("67897.50")
    assert importe_renglon(Decimal("0.10"), Decimal("0.3")) == Decimal("0.03")
    assert importe_renglon(Decimal("3333.33"), Decimal("0.005")) == Decimal("16.67")


def test_precio_propio_del_cliente_pisa_la_lista() -> None:
    precio = resolver_precio(
        "entero", {"entero": Decimal("5000")}, LISTAS, Lista.MAYORISTA, Turno.MANANA, "norte"
    )
    assert precio == Decimal("5000.00")


def test_lista_por_zona_pisa_la_general_y_respeta_el_turno() -> None:
    assert resolver_precio("entero", {}, LISTAS, Lista.MAYORISTA, Turno.MANANA, "norte") == 5400
    assert resolver_precio("entero", {}, LISTAS, Lista.MAYORISTA, Turno.MANANA, "sur") == 5500
    assert resolver_precio("entero", {}, LISTAS, Lista.MAYORISTA, Turno.TARDE, "norte") == 5600
    assert resolver_precio("entero", {}, LISTAS, Lista.MINORISTA, Turno.MANANA, None) == 6500


def test_sin_precio_propio_ni_lista_el_renglon_queda_sin_precio() -> None:
    assert resolver_precio("suprema", {}, LISTAS, Lista.MAYORISTA, Turno.MANANA, None) is None
    assert resolver_precio("alas", {}, LISTAS, Lista.INTERMEDIO, Turno.MANANA, None) is None


@pytest.mark.parametrize("precio", ["0", "-1", "1000000.01"])
def test_precios_fuera_de_rango_se_rechazan(precio: str) -> None:
    with pytest.raises(ErrorDominio):
        validar_precio(Decimal(precio))


def test_renglon_sin_pesar_no_vale_nada_pero_tiene_estimado() -> None:
    renglon = Renglon("entero", Decimal("5500"), kg_pedidos=Decimal("200"))
    assert renglon.importe == 0
    assert renglon.importe_estimado == Decimal("1100000.00")
    assert not renglon.pesado


def test_renglon_por_cajas_no_tiene_estimado_hasta_pesar() -> None:
    renglon = Renglon("alas", Decimal("4150"), cajas=3)
    assert renglon.importe == 0
    assert renglon.importe_estimado == 0


def test_totales_se_calculan_con_lo_pesado_y_avisan_lo_que_falta() -> None:
    totales = totales_pedido(
        [
            Renglon(
                "entero", Decimal("5500"), kg_pedidos=Decimal("200"), kg_pesados=Decimal("198.5")
            ),
            Renglon("alas", Decimal("4150"), cajas=3),
            Renglon("suprema", None, cajas=1),
        ]
    )
    assert totales.subtotal == Decimal("1091750.00")
    assert totales.estimado == Decimal("1091750.00")
    assert totales.sin_precio == ("suprema",)
    assert totales.sin_pesar == ("alas", "suprema")
    assert not totales.completo


def test_pedido_completo_cuando_todo_esta_pesado_y_con_precio() -> None:
    totales = totales_pedido(
        [Renglon("entero", Decimal("5500"), cajas=2, kg_pesados=Decimal("40.25"))]
    )
    assert totales.completo
    assert totales.subtotal == Decimal("221375.00")


def test_pedido_rechaza_productos_repetidos_desconocidos_o_vacios() -> None:
    with pytest.raises(ErrorDominio):
        totales_pedido([])
    with pytest.raises(ErrorDominio, match="repetido"):
        totales_pedido([Renglon("entero", None, cajas=1), Renglon("entero", None, cajas=2)])
    with pytest.raises(ErrorDominio, match="desconocido"):
        totales_pedido([Renglon("trozado", None, cajas=1)])
    with pytest.raises(ErrorDominio, match="cajas o kilos"):
        totales_pedido([Renglon("entero", None)])


@pytest.mark.parametrize("kg", ["0", "-2", "5000.001"])
def test_kilos_pedidos_fuera_de_rango(kg: str) -> None:
    with pytest.raises(ErrorDominio):
        totales_pedido([Renglon("entero", None, kg_pedidos=Decimal(kg))])
