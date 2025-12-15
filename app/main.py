# app/main.py
from fastapi import FastAPI
from app.routers import webhook # <--- Importamos el router

app = FastAPI(title="Optica Bot")

# Conectamos el router del webhook a la app principal
app.include_router(webhook.router)

@app.get("/")
def read_root():
    return {"status": "El sistema está activo", "version": "1.0.0"}
