from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

MENDOZA = ZoneInfo("America/Argentina/Mendoza")


def ahora() -> datetime:
    return datetime.now(UTC)


def hoy() -> date:
    """La fecha operativa es la de Mendoza, no la del servidor."""
    return datetime.now(MENDOZA).date()


def inicio_del_dia(dia: date) -> datetime:
    return datetime.combine(dia, datetime.min.time(), tzinfo=MENDOZA)
