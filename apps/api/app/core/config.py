from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Pollito Casero API"
    entorno: str = "desarrollo"
    zona_horaria: str = "America/Argentina/Mendoza"

    database_url: str = "postgresql+asyncpg://pollito:pollito@localhost:5432/pollito"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "solo-desarrollo-cambiar-en-produccion-por-una-clave-larga"
    jwt_acceso_minutos: int = 15
    jwt_refresh_dias: int = 30

    cors_origins: list[str] = ["http://localhost:8081", "http://localhost:19006"]

    # Archivos (fotos, PDFs, Excel) y URL con la que la app llega a la API para descargarlos.
    data_dir: str = "./data"
    url_publica: str = "http://localhost:8000"
    # "inline" ejecuta las tareas del worker en el mismo proceso (desarrollo sin Redis, tests);
    # "arq" las encola en Redis para el worker.
    worker_modo: str = "inline"

    # Google Maps Platform, solo del lado del servidor (Geocoding API). Vacío = sin geocoding.
    google_maps_api_key: str = ""

    # Datos fiscales impresos en el remito.
    fiscal_razon_social: str = "EL POLLITO CASERO"
    fiscal_lema: str = "VENTA POR MAYOR Y MENOR"
    fiscal_cuit: str = "20-38910784-1"
    fiscal_iibb: str = "0713799"
    fiscal_inicio_actividades: str = "17/11/2014"
    fiscal_condicion_iva: str = "IVA RESPONSABLE INSCRIPTO"
    fiscal_domicilio: str = "Carril Norte S/N - El Ramblón, Mendoza"
    fiscal_whatsapp: str = "+54 9 2634 56-9139"


@lru_cache
def get_settings() -> Settings:
    return Settings()
