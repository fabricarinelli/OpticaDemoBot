# app/scripts/test_agendar.py
import sys
import os
import datetime
from dotenv import load_dotenv

# 1. Configuración de rutas para que Python encuentre 'app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from app.core.database import SessionLocal
from app.models.models import Professional, ProfessionalType
from app.services.calendar import agendar_evento


def test_agendar_turno():
    db = SessionLocal()

    print("🧪 TEST DE AGENDAMIENTO (GOOGLE CALENDAR)")
    print("=" * 50)

    # 1. Buscamos un profesional para la prueba
    # OJO: Asegúrate de que este profesional tenga un calendar_id válido donde tu
    # Service Account tenga permisos de escritura.
    profesional = db.query(Professional).filter(Professional.type == ProfessionalType.OPTICO).first()

    if not profesional:
        print("❌ No encontré ningún óptico en la base de datos. Corre init_db.py primero.")
        return

    print(f"👨‍⚕️ Profesional elegido: {profesional.name}")
    print(f"📅 ID Calendario: {profesional.calendar_id}")

    # 2. Definimos fecha: Mañana a las 10:00 AM
    manana = datetime.date.today() + datetime.timedelta(days=1)
    hora_inicio = datetime.datetime.combine(manana, datetime.time(10, 0))  # 10:00 AM

    # Formato ISO string que espera la función
    start_time_iso = hora_inicio.isoformat()

    # 3. Datos del cliente ficticio
    cliente_nombre = "Test Script User"
    cliente_email = "fabricarinelli@gmail.com"  # Pon tu email real para recibir la invitación y verificar

    print(f"\n🚀 Intentando agendar turno para: {start_time_iso}")

    # 4. Llamada a la función
    resultado = agendar_evento(
        calendar_id=profesional.calendar_id,
        start_time=start_time_iso,
        client_name=cliente_nombre,
        client_email=cliente_email
    )

    # 5. Verificación
    if resultado.get("status") == "success":
        print("\n✅ ¡ÉXITO! Turno agendado en Google Calendar.")
        print(f"🔗 Link del evento: {resultado.get('link')}")
        print(f"🆔 ID del evento: {resultado.get('id')}")
    else:
        print("\n❌ FALLÓ. Hubo un error al conectar con Google.")
        print(f"Error: {resultado.get('message')}")

    db.close()


if __name__ == "__main__":
    test_agendar_turno()