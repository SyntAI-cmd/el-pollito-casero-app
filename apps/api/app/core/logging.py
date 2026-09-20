import logging

import structlog


def configurar_logging(entorno: str) -> None:
    """JSON en producción, consola legible en desarrollo."""
    renderer: structlog.types.Processor = (
        structlog.dev.ConsoleRenderer()
        if entorno == "desarrollo"
        else structlog.processors.JSONRenderer()
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    )
