from app.domain.telefonos import normalizar_telefono


def test_normaliza_formatos_argentinos_habituales() -> None:
    assert normalizar_telefono("2635551234") == "5492635551234"
    assert normalizar_telefono("0263 15 555-1234") == "5492635551234"
    assert normalizar_telefono("+54 9 263 555 1234") == "5492635551234"
    assert normalizar_telefono("+54 263 555 1234") == "5492635551234"
    assert normalizar_telefono("11 2345 6789") == "5491123456789"


def test_rechaza_lo_que_no_es_un_telefono() -> None:
    assert normalizar_telefono("1234") is None
    assert normalizar_telefono("") is None
    assert normalizar_telefono(None) is None
