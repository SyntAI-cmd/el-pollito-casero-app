"""Cierre de caja por persona y día: efectivo que debía rendir contra lo recibido."""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.domain.dinero import CERO, a_importe
from app.domain.errores import ErrorDominio
from app.domain.pagos import Medio, ParteCobro


@dataclass(frozen=True)
class ResumenCaja:
    efectivo_esperado: Decimal
    transferencias: Decimal
    cheques: Decimal
    cantidad_cobros: int

    @property
    def total_cobrado(self) -> Decimal:
        return self.efectivo_esperado + self.transferencias + self.cheques


def resumir_caja(partes: Sequence[ParteCobro]) -> ResumenCaja:
    """
    Solo el efectivo se rinde en mano. Transferencias y cheques se listan aparte y NO suman al
    efectivo a rendir: ya están en el banco o en papel, no en el bolsillo del cobrador.
    """
    por_medio = {medio: CERO for medio in Medio}
    for parte in partes:
        por_medio[parte.medio] += a_importe(parte.importe)
    return ResumenCaja(
        efectivo_esperado=por_medio[Medio.EFECTIVO],
        transferencias=por_medio[Medio.TRANSFERENCIA],
        cheques=por_medio[Medio.CHEQUE],
        cantidad_cobros=len(partes),
    )


@dataclass(frozen=True)
class Cierre:
    efectivo_esperado: Decimal
    efectivo_recibido: Decimal
    nota: str

    @property
    def diferencia(self) -> Decimal:
        """Recibido − esperado: negativa es faltante, positiva es sobrante."""
        return self.efectivo_recibido - self.efectivo_esperado

    @property
    def cuadra(self) -> bool:
        return self.diferencia == CERO


def cerrar_caja(resumen: ResumenCaja, efectivo_recibido: Decimal, nota: str = "") -> Cierre:
    efectivo_recibido = a_importe(efectivo_recibido)
    if efectivo_recibido < CERO:
        raise ErrorDominio("El efectivo recibido no puede ser negativo")
    cierre = Cierre(resumen.efectivo_esperado, efectivo_recibido, nota.strip())
    if not cierre.cuadra and not cierre.nota:
        raise ErrorDominio(f"La caja no cuadra (diferencia {cierre.diferencia}): anotá el motivo")
    return cierre
