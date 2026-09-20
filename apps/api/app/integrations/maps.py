"""
Mapas detrás de una interfaz: geocoding (dirección → coordenadas), rutas y optimización de paradas.
La API key vive solo acá, en el servidor; la app nunca llama a Google directamente.

Con `GOOGLE_MAPS_API_KEY` en el entorno se usa la Geocoding API de Google acotada a Mendoza;
sin la clave, el proveedor nulo deja la ficha sin coordenadas y marcada para revisar.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

import httpx

from app.core.config import get_settings

log = logging.getLogger(__name__)
PRECISION = Decimal("0.000001")


def _rectangulo(sur_oeste: tuple[Decimal, Decimal], nor_este: tuple[Decimal, Decimal]) -> str:
    return f"{sur_oeste[0]},{sur_oeste[1]}|{nor_este[0]},{nor_este[1]}"


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


class GeocodificadorGoogle:
    """
    Geocoding API de Google. Se pide siempre dentro del este de Mendoza (`bounds`) y en Argentina
    (`region=ar`, `components=country:AR`), y se descartan los resultados que caen fuera del
    rectángulo o que Google no pudo ubicar a nivel calle: mejor "revisar" que un punto en otra
    provincia.
    """

    URL = "https://maps.googleapis.com/maps/api/geocode/json"
    # Rectángulo: San Martín, Junín, Rivadavia, Santa Rosa, Lavalle, Maipú y el Gran Mendoza.
    SUR_OESTE = (Decimal("-33.60"), Decimal("-69.10"))
    NOR_ESTE = (Decimal("-32.40"), Decimal("-67.90"))
    PRECISIONES_VALIDAS = {"ROOFTOP", "RANGE_INTERPOLATED", "GEOMETRIC_CENTER"}

    def __init__(self, api_key: str, provincia: str = "Mendoza") -> None:
        self.api_key = api_key
        self.provincia = provincia

    async def geocodificar(self, direccion: str, localidad: str) -> Coordenadas | None:
        if not direccion.strip():
            return None
        consulta = ", ".join(x for x in (direccion.strip(), localidad.strip(), self.provincia) if x)
        parametros = {
            "address": consulta,
            "key": self.api_key,
            "region": "ar",
            "language": "es",
            "components": "country:AR",
            "bounds": _rectangulo(self.SUR_OESTE, self.NOR_ESTE),
        }
        try:
            async with httpx.AsyncClient(timeout=8) as cliente:
                respuesta = await cliente.get(self.URL, params=parametros)
                respuesta.raise_for_status()
                datos = respuesta.json()
        except (httpx.HTTPError, ValueError) as error:
            # Un geocoding perdido no puede impedir dar de alta al cliente.
            log.warning("Geocoding sin respuesta para %r: %s", consulta, error)
            return None
        if datos.get("status") != "OK":
            log.info("Geocoding %s para %r", datos.get("status"), consulta)
            return None
        for resultado in datos.get("results", []):
            if resultado.get("geometry", {}).get("location_type") not in self.PRECISIONES_VALIDAS:
                continue
            ubicacion = resultado["geometry"]["location"]
            lat, lng = Decimal(str(ubicacion["lat"])), Decimal(str(ubicacion["lng"]))
            dentro = (
                self.SUR_OESTE[0] <= lat <= self.NOR_ESTE[0]
                and self.SUR_OESTE[1] <= lng <= self.NOR_ESTE[1]
            )
            if dentro:
                return Coordenadas(lat=lat.quantize(PRECISION), lng=lng.quantize(PRECISION))
        return None


_geocodificador: Geocodificador | None = None


def geocodificador() -> Geocodificador:
    global _geocodificador
    if _geocodificador is None:
        clave = get_settings().google_maps_api_key
        _geocodificador = GeocodificadorGoogle(clave) if clave else GeocodificadorNulo()
    return _geocodificador


def usar_geocodificador(implementacion: Geocodificador) -> None:
    global _geocodificador
    _geocodificador = implementacion
