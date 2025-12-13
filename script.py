import requests
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("INSTAGRAM_TOKEN")
IG_ID = os.getenv("INSTAGRAM_ID") # Es el 1784...

# CAMBIO: Usamos el ID de INSTAGRAM en lugar del ID de la página
url = f"https://graph.facebook.com/v21.0/{IG_ID}/subscribed_apps"

params = {
    # El campo es 'messaging', no 'messages' al suscribir IGID.
    "subscribed_fields": "messaging",
    "access_token": TOKEN
}

print(f"🔌 Intentando conectar IGID {IG_ID} a la App...")
response = requests.post(url, params=params)

print(f"Estado HTTP: {response.status_code}")
print("Respuesta:", response.json())

if response.status_code == 200 and response.json().get("success"):
    print("\n✅ ¡ÉXITO TOTAL! Suscripción directa al IGID.")
else:
    print("\n❌ FALLÓ. Revisar error.")