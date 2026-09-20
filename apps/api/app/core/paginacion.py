from typing import Annotated

from fastapi import Query
from pydantic import BaseModel


class Pagina(BaseModel):
    limite: int = 50
    desde: int = 0


def pagina(
    limite: Annotated[int, Query(ge=1, le=500)] = 50,
    desde: Annotated[int, Query(ge=0)] = 0,
) -> Pagina:
    return Pagina(limite=limite, desde=desde)
