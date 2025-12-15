import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ Error: No se encontró GEMINI_API_KEY en el archivo .env")
else:
    print(f"🔑 Usando API Key: {api_key[:5]}...*****")
    genai.configure(api_key=api_key)

    print("\n📡 Consultando modelos disponibles en Google AI...")
    try:
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f" - {m.name}")
                available_models.append(m.name)

        if not available_models:
            print("⚠️ No se encontraron modelos de generación de contenido. Revisa los permisos de tu API Key.")
    except Exception as e:
        print(f"❌ Error al conectar: {e}")