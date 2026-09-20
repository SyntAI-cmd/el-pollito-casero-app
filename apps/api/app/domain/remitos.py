"""El número de pedido es el número de remito: correlativo de 5 dígitos, el mismo en todos lados."""

from app.domain.errores import ErrorDominio

NUMERO_MAXIMO = 99_999


def formatear_numero(numero: int) -> str:
    if numero < 1 or numero > NUMERO_MAXIMO:
        raise ErrorDominio(f"Número de remito fuera de rango: {numero}")
    return f"{numero:05d}"


def siguiente_numero(ultimo: int | None) -> int:
    siguiente = (ultimo or 0) + 1
    if siguiente > NUMERO_MAXIMO:
        raise ErrorDominio(
            "Se agotó la numeración de remitos (99999). Hay que abrir una serie nueva."
        )
    return siguiente
