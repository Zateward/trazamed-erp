from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Hospitraze ERP"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production-use-256-bit-random-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://hospitraze:hospitraze@db:5432/hospitraze"
    DATABASE_URL_SYNC: str = "postgresql://hospitraze:hospitraze@db:5432/hospitraze"

    # Redis (Celery broker)
    REDIS_URL: str = "redis://redis:6379/0"

    # MQTT (IoT sensors)
    MQTT_BROKER: str = "mqtt"
    MQTT_PORT: int = 1883
    MQTT_TOPIC_COLD_CHAIN: str = "hospitraze/coldchain/#"
    MQTT_TOPIC_RFID: str = "hospitraze/rfid/#"

    # AI / LLM
    OPENAI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    LLM_PROVIDER: str = "gemini"  # "openai" | "gemini"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    CHROMA_HOST: str = "chromadb"
    CHROMA_PORT: int = 8000

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://frontend:3000"]

    # NOM compliance
    FIRMA_ELECTRONICA_ENABLED: bool = True
    AUDIT_LOG_RETENTION_DAYS: int = 3650  # 10 years per NOM-024

    class Config:
        env_file = ".env"
        case_sensitive = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.DEBUG and self.SECRET_KEY == "change-me-in-production-use-256-bit-random-key":
            raise ValueError(
                "SECRET_KEY must be changed in production. "
                "Set a secure 256-bit random key in your environment."
            )


settings = Settings()
