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

    # Mercado Pago
    MP_ACCESS_TOKEN: str
    MP_PUBLIC_KEY: str

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()