"""
Object storage detrás de una interfaz: fotos de comprobantes, remitos firmados, PDFs y Excel.
Implementación local en disco con URL firmada (HMAC con vencimiento) servida por la propia API;
S3/R2 entra sin tocar los módulos.
"""

import hashlib
import hmac
import time
from pathlib import Path
from typing import Protocol
from urllib.parse import quote

from app.core.config import get_settings


class Storage(Protocol):
    async def guardar(self, clave: str, contenido: bytes, tipo: str) -> None: ...
    async def leer(self, clave: str) -> tuple[bytes, str] | None: ...
    def url_firmada(self, clave: str, minutos: int = 30) -> str: ...


def _firma(clave: str, vence: int) -> str:
    mensaje = f"{clave}:{vence}".encode()
    return hmac.new(get_settings().jwt_secret.encode(), mensaje, hashlib.sha256).hexdigest()


def firma_valida(clave: str, vence: int, firma: str) -> bool:
    return vence >= int(time.time()) and hmac.compare_digest(_firma(clave, vence), firma)


class StorageLocal:
    """Archivos bajo DATA_DIR/archivos. Guarda el content-type en un archivo al lado."""

    def __init__(self, raiz: Path | None = None) -> None:
        self.raiz = raiz or Path(get_settings().data_dir) / "archivos"

    def _ruta(self, clave: str) -> Path:
        ruta = (self.raiz / clave).resolve()
        if self.raiz.resolve() not in ruta.parents:
            raise ValueError("Clave de archivo inválida")
        return ruta

    async def guardar(self, clave: str, contenido: bytes, tipo: str) -> None:
        ruta = self._ruta(clave)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_bytes(contenido)
        ruta.with_suffix(ruta.suffix + ".tipo").write_text(tipo, encoding="utf-8")

    async def leer(self, clave: str) -> tuple[bytes, str] | None:
        ruta = self._ruta(clave)
        if not ruta.exists():
            return None
        tipo_ruta = ruta.with_suffix(ruta.suffix + ".tipo")
        tipo = (
            tipo_ruta.read_text(encoding="utf-8")
            if tipo_ruta.exists()
            else "application/octet-stream"
        )
        return ruta.read_bytes(), tipo

    def url_firmada(self, clave: str, minutos: int = 30) -> str:
        vence = int(time.time()) + minutos * 60
        base = get_settings().url_publica.rstrip("/")
        return f"{base}/archivos/{quote(clave)}?vence={vence}&firma={_firma(clave, vence)}"


_storage: Storage | None = None


def storage() -> Storage:
    global _storage
    if _storage is None:
        _storage = StorageLocal()
    return _storage


def usar_storage(implementacion: Storage) -> None:
    global _storage
    _storage = implementacion
