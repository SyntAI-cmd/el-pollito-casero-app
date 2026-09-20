"""Tipos Pydantic compartidos: importes y kilos siempre salen con la misma cantidad de decimales."""

from decimal import Decimal
from typing import Annotated

from pydantic import PlainSerializer

from app.domain.dinero import a_importe, a_kilos

Importe = Annotated[Decimal, PlainSerializer(lambda v: str(a_importe(v)), return_type=str)]
Kilos = Annotated[Decimal, PlainSerializer(lambda v: str(a_kilos(v)), return_type=str)]
