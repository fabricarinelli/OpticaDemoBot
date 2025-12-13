# app/core/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # App
    PROJECT_NAME: str = "Optica Bot"
    VERSION: str = "1.0.0"

    # Database
    DATABASE_URL: str

    # WhatsApp (Meta)
    INSTAGRAM_TOKEN: str
    INSTAGRAM_ID: str
    INSTAGRAM_VERIFY_TOKEN: str
    class Config:
        env_file = ".env"
        case_sensitive = True

    # Google (Gemini & Calendar)
    GEMINI_API_KEY: str

    # Mercado Pago
    MP_ACCESS_TOKEN: str

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()