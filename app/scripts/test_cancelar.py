# app/scripts/test_cancelar.py
import sys
import os
import datetime
import time
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

from app.core.database import SessionLocal
from app.models.models import Professional, ProfessionalType
from app.services.calendar import agendar_evento, cancelar_evento


def test_ciclo_agendar_cancelar():
    db = SessionLocal()
    print("🧪 TEST: AGENDAR Y CANCELAR (Ciclo Completo)")
    print("=" * 50)

    # 1. Obtener profesional
    profesional = db.query(Professional).filter(Professional.type == ProfessionalType.OPTICO).first()
    if not profesional:
        print("❌ Faltan profesionales en la DB.")
        return

    # 2. Agendar un turno 'dummy' para dentro de 2 días
    fecha_prueba = (datetime.date.today() + datetime.timedelta(days=2)).isoformat()
    hora_prueba = f"{fecha_prueba}T11:00:00"

    print(f"1️⃣ Agendando turno de prueba para: {hora_prueba}...")

    resultado_agenda = agendar_evento(
        calendar_id=profesional.calendar_id,
        start_time=hora_prueba,
        client_name="TEST BORRAR",
        client_email=None
    )

    if resultado_agenda["status"] != "success":
        print(f"❌ Falló al agendar: {resultado_agenda['message']}")
        return
    event_id = resultado_agenda["id"]
    link = resultado_agenda.get('link')
    print(f"✅ Agendado con éxito. ID Google: {link}")
    print("   (Verifica tu calendario, debería aparecer el turno)")

    # 3. Esperar unos segundos para dar drama (y tiempo a ver el calendario si quieres)
    for i in range(60):
        time.sleep(1)
        print(f"\n⏳ Esperando {60-i} segundos antes de eliminar...")




    # 4. Cancelar el turno
    print(f"\n2️⃣ Intentando eliminar el evento {event_id}...")
    resultado_cancelar = cancelar_evento(
        calendar_id=profesional.calendar_id,
        event_id=event_id
    )

    if resultado_cancelar["status"] == "success":
        print("✅ ¡ÉXITO! El turno fue eliminado del calendario.")
        print("   (El horario ha quedado libre nuevamente)")
    else:
        print(f"❌ Falló al cancelar: {resultado_cancelar['message']}")

    db.close()


if __name__ == "__main__":
    test_ciclo_agendar_cancelar()