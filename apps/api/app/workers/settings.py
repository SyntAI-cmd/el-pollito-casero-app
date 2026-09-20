"""Configuración del worker de arq: `uv run arq app.workers.settings.WorkerSettings`."""

from app.workers.cola import redis_settings
from app.workers.tareas import generar_documento


class WorkerSettings:
    functions = [generar_documento]
    redis_settings = redis_settings()
    max_jobs = 4
    job_timeout = 300
