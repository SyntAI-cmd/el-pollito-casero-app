"""
Encolado de tareas. Modo "arq": Redis + worker aparte
(`uv run arq app.workers.settings.WorkerSettings`).
Modo "inline": la tarea corre en el mismo proceso, al final de la petición (desarrollo sin Redis
y tests). Los módulos llaman a `encolar` y no saben cuál de los dos hay.
"""

import asyncio
import logging
from typing import Any

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.core.config import get_settings

log = logging.getLogger(__name__)
_pool: ArqRedis | None = None
_inline_en_espera: set[asyncio.Task[Any]] = set()


def redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(get_settings().redis_url)


async def encolar(tarea: str, *args: Any) -> None:
    if get_settings().worker_modo == "arq":
        global _pool
        if _pool is None:
            _pool = await create_pool(redis_settings())
        await _pool.enqueue_job(tarea, *args)
        return
    from app.workers import tareas  # importa acá para no cargar ReportLab al arrancar la API

    funcion = getattr(tareas, tarea)
    ejecucion = asyncio.create_task(funcion({}, *args))
    _inline_en_espera.add(ejecucion)
    ejecucion.add_done_callback(_inline_en_espera.discard)


async def esperar_inline() -> None:
    """Para tests: espera a que terminen las tareas lanzadas en modo inline."""
    if _inline_en_espera:
        await asyncio.gather(*_inline_en_espera, return_exceptions=True)
