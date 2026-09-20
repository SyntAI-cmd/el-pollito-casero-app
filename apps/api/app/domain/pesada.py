"""Pesada: se pesa bruto, se resta la tara del cajón y queda el neto que se cobra."""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal

from app.domain.dinero import CERO, GRAMO, a_kilos
from app.domain.errores import ErrorDominio

TARA_POR_DEFECTO = Decimal("1.7")
BRUTO_MAXIMO = Decimal("5000")


def validar_tara(tara: Decimal) -> Decimal:
    tara = a_kilos(tara)
    if tara < CERO or tara > Decimal("20"):
        raise ErrorDominio(f"Tara inválida: {tara} kg")
    return tara


def neto(bruto: Decimal, tara: Decimal = TARA_POR_DEFECTO) -> Decimal:
    bruto = a_kilos(bruto)
    tara = validar_tara(tara)
    if bruto <= CERO or bruto > BRUTO_MAXIMO:
        raise ErrorDominio(f"Peso bruto inválido: {bruto} kg")
    resultado = bruto - tara
    if resultado <= CERO:
        raise ErrorDominio(f"El bruto ({bruto} kg) no supera la tara ({tara} kg)")
    return resultado


def repartir_lote(
    cajas: int, bruto_total: Decimal, tara: Decimal = TARA_POR_DEFECTO
) -> list[Decimal]:
    """
    Pesada por lote: N cajas con un solo bruto total. Se descuenta la tara de cada cajón ANTES de
    repartir, así el neto total es exacto y cada cajón queda como fila propia (carga y remito
    siguen contando cajas). El resto del redondeo va al último cajón para que la suma cierre.
    """
    if cajas < 1 or cajas > 500:
        raise ErrorDominio("Un lote lleva entre 1 y 500 cajas")
    tara = validar_tara(tara)
    bruto_total = a_kilos(bruto_total)
    neto_total = bruto_total - tara * cajas
    if bruto_total <= CERO or bruto_total > BRUTO_MAXIMO or neto_total <= CERO:
        raise ErrorDominio(
            f"El bruto del lote ({bruto_total} kg) no alcanza para {cajas} cajas con tara {tara} kg"
        )
    por_cajon = (neto_total / cajas).quantize(GRAMO, rounding=ROUND_DOWN)
    netos = [por_cajon] * cajas
    netos[-1] = neto_total - por_cajon * (cajas - 1)
    return netos


@dataclass(frozen=True)
class Cajon:
    """Cada cajón es una fila con id propia: se anula con motivo y se marca cargado al camión."""

    id: str
    producto_id: str
    neto: Decimal
    cargado: bool = False
    anulado: bool = False
    motivo_anulacion: str | None = None


def agregar_cajon(existentes: Sequence[Cajon], nuevo: Cajon) -> list[Cajon]:
    """Idempotente: un reintento con el mismo id (offline) no duplica el cajón."""
    if any(c.id == nuevo.id for c in existentes):
        return list(existentes)
    return [*existentes, nuevo]


def anular_cajon(cajon: Cajon, motivo: str) -> Cajon:
    motivo = motivo.strip()
    if len(motivo) < 3:
        raise ErrorDominio("Indicá el motivo de la anulación")
    if cajon.cargado:
        raise ErrorDominio("Un cajón ya cargado al camión no se anula: bajalo primero")
    return Cajon(
        id=cajon.id,
        producto_id=cajon.producto_id,
        neto=cajon.neto,
        anulado=True,
        motivo_anulacion=motivo,
    )


def marcar_cargado(cajon: Cajon) -> Cajon:
    if cajon.anulado:
        raise ErrorDominio("Un cajón anulado no se carga")
    return Cajon(id=cajon.id, producto_id=cajon.producto_id, neto=cajon.neto, cargado=True)


def kilos_por_producto(cajones: Sequence[Cajon]) -> dict[str, Decimal]:
    """Neto acumulado por producto, ignorando anulados. Es lo que va al renglón como kg_pesados."""
    acumulado: dict[str, Decimal] = {}
    for cajon in cajones:
        if cajon.anulado:
            continue
        acumulado[cajon.producto_id] = acumulado.get(cajon.producto_id, CERO) + cajon.neto
    return acumulado
