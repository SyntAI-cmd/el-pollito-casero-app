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


@lru_cache
def get_settings() -> Settings:
    return Settings()
