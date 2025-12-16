# app/core/config.py
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    # App
    PROJECT_NAME: str = "Optica Bot"
    VERSION: str = "1.0.0"

    # Database
    DATABASE_URL: str

    # Meta (Instagram)
    INSTAGRAM_TOKEN: str
    INSTAGRAM_ID: str
    INSTAGRAM_VERIFY_TOKEN: str

    # Google (Gemini & Calendar)
    GEMINI_API_KEY: str
    GOOGLE_APPLICATION_CREDENTIALS: str
    ADMIN_EMAIL: str
    BARBER_CALENDAR_ID: str

    # Mercado Pago
    MP_ACCESS_TOKEN: str
    MP_PUBLIC_KEY: str

    CATALOG_IMAGE_URL: str

    model_config = SettingsConfigDict(
        env_file="/home/fabri/Escritorio/optica-bot/.env",  # <-- Le pasamos la ruta absoluta
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra='ignore'  # Si hay variables de más en el .env, no explota
    )


@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()