# app/routers/webhook.py
from fastapi import APIRouter, Request, HTTPException, Query
from app.core.config import settings

router = APIRouter()


# --- PARTE 1: VERIFICACIÓN (HANDSHAKE) ---
# Meta llama aquí con un GET para ver si eres tú.
@router.get("/webhook")
async def verify_webhook(
        mode: str = Query(alias="hub.mode"),
        token: str = Query(alias="hub.verify_token"),
        challenge: str = Query(alias="hub.challenge")
):
    # Verificamos si el token que manda Meta coincide con el que pusimos en .env
    if mode == "subscribe" and token == settings.INSTAGRAM_VERIFY_TOKEN:
        print(f"✅ Webhook verificado exitosamente. Challenge: {challenge}")
        return int(challenge)

    print(f"❌ Falló la verificación. Token recibido: {token} vs Esperado: {settings.INSTAGRAM_VERIFY_TOKEN}")
    raise HTTPException(status_code=403, detail="Token de verificación incorrecto")


# --- PARTE 2: RECEPCIÓN DE MENSAJES ---
# Aquí llegarán los mensajes de los usuarios (POST)
@router.post("/webhook")
async def receive_instagram_message(request: Request):
    try:
        payload = await request.json()
        print("📩 Payload recibido:", payload)  # Esto lo veremos en la terminal

        # Aquí luego procesaremos el mensaje...

        return {"status": "received"}
    except Exception as e:
        print(f"⚠️ Error procesando mensaje: {e}")
        return {"status": "error"}