"""Tipos de columna compartidos. Importes NUMERIC(12,2), kilos NUMERIC(9,3): jamás float."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator

IMPORTE = Numeric(12, 2)
KILOS = Numeric(9, 3)

# JSONB en Postgres; JSON plano en SQLite (solo tests locales sin Docker).
JSON_FLEX = JSON().with_variant(JSONB(), "postgresql")


def enum_sql(enum: type[StrEnum], nombre: str) -> Enum:
    """Guarda el valor ("mayorista") y no el nombre ("MAYORISTA") del enum."""

    def valores(e: Any) -> list[str]:
        return [x.value for x in e]

    return Enum(enum, name=nombre, values_callable=valores)


class FechaHora(TypeDecorator[datetime]):
    """TIMESTAMPTZ. SQLite devuelve fechas sin zona: se las vuelve a poner en UTC al leer."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("Las fechas se guardan siempre con zona horaria")
        return value

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
