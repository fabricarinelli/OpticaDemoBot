# app/scripts/test_instagram.py
import asyncio
import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
load_dotenv()

from app.services.instagram import send_text, send_image
from app.core.config import settings

# ¡PON AQUÍ TU ID DE USUARIO (EL QUE SALE EN EL WEBHOOK)!
MI_ID_DE_PRUEBA = "1358917032599411"


async def probar_instagram():
    print("📢 TEST DE INSTAGRAM (LA BOCA)")
    print("=" * 50)

    # 1. Prueba de Texto
    print(f"💬 Enviando saludo a {MI_ID_DE_PRUEBA}...")
    res_text = await send_text(MI_ID_DE_PRUEBA, "¡Hola! Soy la IA de Óptica Demo. 🤖")

    if res_text["status"] == "success":
        print("✅ Texto enviado correctamente.")
    else:
        print(f"❌ Falló el texto: {res_text['message']}")

    # 2. Prueba de Imagen (Catálogo)
    print(f"\n📸 Enviando imagen de catálogo...")
    # Usamos la URL del catálogo que pusimos en .env o una de prueba
    url_imagen = settings.CATALOG_IMAGE_URL

    res_img = await send_image(MI_ID_DE_PRUEBA, url_imagen)

    if res_img["status"] == "success":
        print("✅ Imagen enviada correctamente.")
    else:
        print(f"❌ Falló la imagen: {res_img['message']}")


if __name__ == "__main__":
    if MI_ID_DE_PRUEBA == "PON_TU_ID_AQUI_O_NO_LLEGARA":
        print("⚠️ ALERTA: Debes poner tu ID de Instagram en la variable MI_ID_DE_PRUEBA del script.")
    else:
        asyncio.run(probar_instagram())