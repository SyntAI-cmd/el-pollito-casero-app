from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.errores import registrar_manejadores
from app.core.logging import configurar_logging
from app.core.ws_router import router as ws_router
from app.modules.auth.router import router as auth_router
from app.modules.catalogo.router import router as catalogo_router
from app.modules.clientes.router import router as clientes_router
from app.modules.cobros.router import router as cobros_router
from app.modules.comunicacion.router import router as comunicacion_router
from app.modules.documentos.router import router as documentos_router
from app.modules.flota.router import router as flota_router
from app.modules.pedidos.router import router as pedidos_router
from app.modules.pesada.router import router as pesada_router
from app.modules.sucursales.router import router as sucursales_router


class Salud(BaseModel):
    estado: str
    entorno: str
    version: str


def crear_app() -> FastAPI:
    settings = get_settings()
    configurar_logging(settings.entorno)
    app = FastAPI(title=settings.app_name, version="0.6.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    registrar_manejadores(app)

    @app.get("/health", response_model=Salud, tags=["sistema"])
    async def health() -> Salud:
        return Salud(estado="ok", entorno=settings.entorno, version=app.version)

    app.include_router(auth_router)
    app.include_router(sucursales_router)
    app.include_router(catalogo_router)
    app.include_router(clientes_router)
    app.include_router(pedidos_router)
    app.include_router(pesada_router)
    app.include_router(flota_router)
    app.include_router(cobros_router)
    app.include_router(documentos_router)
    app.include_router(comunicacion_router)
    app.include_router(ws_router)
    return app


app = crear_app()
