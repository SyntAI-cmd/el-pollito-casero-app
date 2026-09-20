"""Renderers de PDF (ReportLab) y Excel (openpyxl). Puros: reciben un Contexto y devuelven bytes."""

from decimal import Decimal

from app.domain.dinero import a_importe, a_kilos


def pesos(valor: Decimal) -> str:
    entero, decimales = str(a_importe(valor)).split(".")
    negativo = entero.startswith("-")
    entero = entero.lstrip("-")
    miles = f"{int(entero):,}".replace(",", ".")
    return f"{'-' if negativo else ''}$ {miles}" + ("" if decimales == "00" else f",{decimales}")


def kilos(valor: Decimal | None) -> str:
    if valor is None:
        return "—"
    entero, decimales = str(a_kilos(valor)).split(".")
    decimales = decimales.rstrip("0")
    miles = f"{int(entero):,}".replace(",", ".")
    return miles + (f",{decimales}" if decimales else "")
