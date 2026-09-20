"""app/domain no importa FastAPI ni SQLAlchemy: son reglas puras que se testean sin servidor."""

import ast
from pathlib import Path

PROHIBIDOS = ("fastapi", "sqlalchemy", "pydantic", "alembic", "asyncpg", "redis")


def test_el_dominio_no_depende_de_frameworks() -> None:
    raiz = Path(__file__).resolve().parent.parent
    for archivo in raiz.glob("*.py"):
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            modulos: list[str] = []
            if isinstance(nodo, ast.Import):
                modulos = [alias.name for alias in nodo.names]
            elif isinstance(nodo, ast.ImportFrom) and nodo.module:
                modulos = [nodo.module]
            for modulo in modulos:
                assert not modulo.startswith(PROHIBIDOS), f"{archivo.name} importa {modulo}"
