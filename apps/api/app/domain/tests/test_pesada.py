from decimal import Decimal

import pytest

from app.domain.errores import ErrorDominio
from app.domain.pesada import (
    Cajon,
    agregar_cajon,
    anular_cajon,
    kilos_por_producto,
    marcar_cargado,
    neto,
    repartir_lote,
)


def test_neto_resta_la_tara_por_defecto() -> None:
    assert neto(Decimal("21.7")) == Decimal("20.000")
    assert neto(Decimal("10"), tara=Decimal("2")) == Decimal("8.000")


def test_bruto_menor_o_igual_a_la_tara_no_es_una_pesada() -> None:
    with pytest.raises(ErrorDominio):
        neto(Decimal("1.7"))
    with pytest.raises(ErrorDominio):
        neto(Decimal("0"))
    with pytest.raises(ErrorDominio):
        neto(Decimal("-3"))


def test_lote_descuenta_la_tara_de_cada_cajon_antes_de_repartir() -> None:
    # 3 cajas, 65.1 kg bruto → 65.1 − 3 × 1.7 = 60 kg netos → 20 kg por cajón
    netos = repartir_lote(3, Decimal("65.1"))
    assert netos == [Decimal("20.000")] * 3


def test_lote_cierra_exacto_aunque_la_division_no_sea_entera() -> None:
    netos = repartir_lote(3, Decimal("15.1"))  # neto total 10.000
    assert sum(netos) == Decimal("10.000")
    assert netos[:2] == [Decimal("3.333")] * 2
    assert netos[2] == Decimal("3.334")


def test_lote_con_bruto_que_no_cubre_las_taras_se_rechaza() -> None:
    with pytest.raises(ErrorDominio):
        repartir_lote(10, Decimal("17"))
    with pytest.raises(ErrorDominio):
        repartir_lote(0, Decimal("50"))


def test_reintento_con_el_mismo_id_no_duplica_el_cajon() -> None:
    cajon = Cajon("c1", "entero", Decimal("20"))
    lista = agregar_cajon([], cajon)
    lista = agregar_cajon(lista, cajon)
    lista = agregar_cajon(lista, Cajon("c2", "entero", Decimal("19.5")))
    assert [c.id for c in lista] == ["c1", "c2"]


def test_anular_exige_motivo_y_no_permite_anular_lo_cargado() -> None:
    cajon = Cajon("c1", "entero", Decimal("20"))
    with pytest.raises(ErrorDominio):
        anular_cajon(cajon, "  ")
    anulado = anular_cajon(cajon, "Se rompió la caja")
    assert anulado.anulado and anulado.motivo_anulacion == "Se rompió la caja"
    with pytest.raises(ErrorDominio):
        anular_cajon(marcar_cargado(cajon), "tarde")
    with pytest.raises(ErrorDominio):
        marcar_cargado(anulado)


def test_kilos_por_producto_ignora_anulados() -> None:
    cajones = [
        Cajon("a", "entero", Decimal("20")),
        Cajon("b", "entero", Decimal("19.5")),
        Cajon("c", "alas", Decimal("12")),
        anular_cajon(Cajon("d", "alas", Decimal("12")), "repetido"),
    ]
    assert kilos_por_producto(cajones) == {"entero": Decimal("39.5"), "alas": Decimal("12")}
