"""
Mapas detrás de una interfaz: geocoding (dirección → coordenadas), rutas y optimización de paradas.
La API key vive solo acá, en el servidor; la app nunca llama a Google directamente.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class Coordenadas:
    lat: Decimal
    lng: Decimal


class Geocodificador(Protocol):
    async def geocodificar(self, direccion: str, localidad: str) -> Coordenadas | None: ...


class GeocodificadorNulo:
    """Sin proveedor configurado: la ficha queda sin coordenadas y se marca para revisar."""

    async def geocodificar(self, direccion: str, localidad: str) -> Coordenadas | None:
        return None


_geocodificador: Geocodificador = GeocodificadorNulo()


def geocodificador() -> Geocodificador:
    return _geocodificador


def usar_geocodificador(implementacion: Geocodificador) -> None:
    global _geocodificador
    _geocodificador = implementacion
