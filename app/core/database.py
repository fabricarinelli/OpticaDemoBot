# app/core/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Si usamos SQLite, necesitamos este argumento extra para check_same_thread
# Si usas Postgres, connect_args se puede quitar o dejar vacío
connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependencia para obtener la DB en cada request de FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()