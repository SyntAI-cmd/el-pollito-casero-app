"""Estados del pedido y reglas de la salida del camión."""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from app.domain.errores import ErrorDominio
from app.domain.pesada import Cajon


class Estado(StrEnum):
    RECIBIDO = "recibido"
    PREPARANDO = "preparando"
    EN_CAMINO = "en_camino"
    ENTREGADO = "entregado"
    CANCELADO = "cancelado"


TRANSICIONES: dict[Estado, frozenset[Estado]] = {
    Estado.RECIBIDO: frozenset({Estado.PREPARANDO, Estado.EN_CAMINO, Estado.CANCELADO}),
    Estado.PREPARANDO: frozenset({Estado.EN_CAMINO, Estado.CANCELADO}),
    Estado.EN_CAMINO: frozenset({Estado.ENTREGADO, Estado.CANCELADO}),
    Estado.ENTREGADO: frozenset(),
    Estado.CANCELADO: frozenset(),
}


def transicionar(actual: Estado, nuevo: Estado) -> Estado:
    if nuevo not in TRANSICIONES[actual]:
        raise ErrorDominio(f"Un pedido {actual} no puede pasar a {nuevo}")
    return nuevo


MAXIMO_PREVENTISTAS_POR_SALIDA = 2


def validar_preventistas_salida(preventistas: Sequence[str]) -> tuple[str, ...]:
    """Van hasta dos por camión y un preventista va en un solo vehículo por día."""
    unicos = tuple(dict.fromkeys(preventistas))
    if not unicos:
        raise ErrorDominio("La salida necesita al menos un preventista")
    if len(unicos) > MAXIMO_PREVENTISTAS_POR_SALIDA:
        raise ErrorDominio("Un camión lleva como máximo dos preventistas")
    return unicos


@dataclass(frozen=True)
class PedidoParaCargar:
    id: str
    numero: str
    cajas_pedidas: int
    cajones: Sequence[Cajon]


@dataclass(frozen=True)
class Faltante:
    pedido_id: str
    numero: str
    sin_pesar: int
    sin_cargar: int


def faltantes_para_cerrar(pedidos: Sequence[PedidoParaCargar]) -> list[Faltante]:
    """Qué falta pesar o cargar antes de cerrar el camión. Vacío = se puede salir sin motivo."""
    faltantes: list[Faltante] = []
    for pedido in pedidos:
        vivos = [c for c in pedido.cajones if not c.anulado]
        sin_pesar = max(pedido.cajas_pedidas - len(vivos), 0)
        sin_cargar = sum(1 for c in vivos if not c.cargado)
        if sin_pesar or sin_cargar:
            faltantes.append(Faltante(pedido.id, pedido.numero, sin_pesar, sin_cargar))
    return faltantes


def validar_cierre_camion(
    pedidos: Sequence[PedidoParaCargar], motivo: str | None
) -> list[Faltante]:
    """Cerrar con faltantes se permite, pero con motivo escrito: queda en auditoría."""
    faltantes = faltantes_para_cerrar(pedidos)
    if faltantes and not (motivo and motivo.strip()):
        detalle = ", ".join(f"#{f.numero}" for f in faltantes)
        raise ErrorDominio(f"Falta pesar o cargar en {detalle}. Indicá el motivo para salir igual")
    return faltantes
