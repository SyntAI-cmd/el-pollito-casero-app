"""Teléfonos argentinos normalizados a formato internacional sin símbolos (549 + área + número)."""

import re


def normalizar_telefono(crudo: str | None) -> str | None:
    """Devuelve "549XXXXXXXXXX" o None si no parece un número argentino válido."""
    digitos = re.sub(r"\D", "", crudo or "")
    if digitos.startswith("00"):
        digitos = digitos[2:]
    if digitos.startswith("54"):
        digitos = digitos[2:]
        if digitos.startswith("9"):
            digitos = digitos[1:]
    if digitos.startswith("0"):
        digitos = digitos[1:]
    # Quita el "15" de celulares escritos como (263) 15 555-1234.
    if len(digitos) == 12 and re.match(r"^\d{2,4}15", digitos):
        digitos = re.sub(r"^(\d{2,4})15", r"\1", digitos)
    if len(digitos) < 10 or len(digitos) > 11:
        return None
    return "549" + digitos
