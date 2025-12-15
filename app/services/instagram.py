# app/services/instagram.py
import httpx
from app.core.config import settings

# Versión de la API
GRAPH_URL = "https://graph.instagram.com/v21.0"

async def send_text(recipient_id: str, text: str):
    """
    Envía texto a Instagram Direct.
    URL Correcta: /{INSTAGRAM_ID}/messages
    """
    # --- CAMBIO CLAVE: Usamos el ID de Instagram, no "me" ---
    url = f"{GRAPH_URL}/{settings.INSTAGRAM_ID}/messages"

    headers = {
        "Authorization": f"Bearer {settings.INSTAGRAM_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
        # Nota: messaging_type a veces sobra en IG, lo quitamos por seguridad
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=data, headers=headers)
            if response.status_code != 200:
                print(f"⚠️ Error Meta (Texto): {response.text}")
            response.raise_for_status()
            return {"status": "success", "data": response.json()}
        except Exception as e:
            print(f"❌ Error enviando texto: {e}")
            return {"status": "error", "message": str(e)}


async def send_image(recipient_id: str, image_url: str):
    """
    Envía imagen a Instagram Direct.
    """
    # --- CAMBIO CLAVE: Usamos el ID de Instagram, no "me" ---
    url = f"{GRAPH_URL}/{settings.INSTAGRAM_ID}/messages"

    headers = {
        "Authorization": f"Bearer {settings.INSTAGRAM_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "recipient": {"id": recipient_id},
        "message": {
            "attachment": {
                "type": "image",
                "payload": {
                    "url": image_url,
                    "is_reusable": True
                }
            }
        }
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=data, headers=headers)
            if response.status_code != 200:
                print(f"⚠️ Error Meta (Imagen): {response.text}")
            response.raise_for_status()
            return {"status": "success", "data": response.json()}
        except Exception as e:
            print(f"❌ Error enviando imagen: {e}")
            return {"status": "error", "message": str(e)}