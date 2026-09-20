from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.logging import configurar_logging


class Salud(BaseModel):
    estado: str
    entorno: str
    version: str


def crear_app() -> FastAPI:
    settings = get_settings()
    configurar_logging(settings.entorno)
    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", response_model=Salud, tags=["sistema"])
    async def health() -> Salud:
        return Salud(estado="ok", entorno=settings.entorno, version=app.version)

    return app


app = crear_app()
