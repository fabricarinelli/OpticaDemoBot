# test_calendar.py
from dotenv import load_dotenv
import datetime
import os
import sys

load_dotenv()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.services.calendar import consultar_disponibilidad


def probar_v2():
    db = SessionLocal()
    manana = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()

    print("🧪 TEST LOGICA DE NEGOCIO V2")
    print("=" * 50)

    # 1. Sin Fecha + Rango (Debe buscar el primer día libre)
    print("\n1️⃣ CASO: 'Quiero turno a la mañana' (Sin decir día)")
    filtros_1 = [{"time_range": (9, 13)}]
    print(consultar_disponibilidad(db, filtros_1, "optico"))

    # 2. Hora Puntual (Debe buscar exacto)
    print(f"\n2️⃣ CASO: 'Mañana a las 10:00 puntual' ({manana})")
    filtros_2 = [{"date": manana, "specific_time": "10:00"}]
    print(consultar_disponibilidad(db, filtros_2, "optico"))

    # 3. Rango Amplio (Debe dar 3 opciones variadas)
    print(f"\n3️⃣ CASO: 'Mañana por la tarde' (Rango 16-20)")
    filtros_3 = [{"date": manana, "time_range": (16, 20)}]
    print(consultar_disponibilidad(db, filtros_3, "optico"))

    db.close()


if __name__ == "__main__":
    probar_v2()