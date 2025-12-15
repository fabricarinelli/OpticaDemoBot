# app/services/tools.py
import datetime
import os.path
from typing import List, Optional
from zoneinfo import ZoneInfo

from google.oauth2 import service_account
from googleapiclient.discovery import build
from sqlalchemy.orm import Session
from app.core.config import settings
from app.services import crud
from app.models.models import ProfessionalType

# --- CONFIGURACIÓN ---
SCOPES = ['https://www.googleapis.com/auth/calendar']
TZ_ARG = ZoneInfo("America/Argentina/Cordoba")

# Duración de turnos
DURATION_MAP = {
    ProfessionalType.OPTICO: 20,
    ProfessionalType.CONTACTOLOGO: 30
}

# Horarios de Atención General
WORK_HOURS = {
    "start": 9, "end": 20  # Simplificado: 9 a 20 de corrido para búsqueda
}


def get_calendar_service():
    """Autentica y retorna el servicio de Google Calendar."""
    creds = None
    service_account_path = settings.GOOGLE_APPLICATION_CREDENTIALS

    if os.path.exists(service_account_path):
        creds = service_account.Credentials.from_service_account_file(
            service_account_path, scopes=SCOPES
        )
    else:
        print(f"❌ Error CRÍTICO: No se encuentra el JSON en {service_account_path}")
        return None

    return build('calendar', 'v3', credentials=creds)


# --- MOTORES DE BÚSQUEDA ---

def check_slot_availability(service, professionals, slot_start, duration):
    """
    Verifica si AL MENOS UN profesional está libre en ese horario exacto.
    Retorna: (True/False, NombreProfesional)
    """
    slot_end = slot_start + datetime.timedelta(minutes=duration)

    for prof in professionals:
        if not prof.calendar_id: continue

        # Consultar eventos en ese micro-rango
        time_min = slot_start.isoformat()
        time_end = slot_end.isoformat()

        try:
            events_result = service.events().list(
                calendarId=prof.calendar_id,
                timeMin=time_min, timeMax=time_end,
                singleEvents=True
            ).execute()
            events = events_result.get('items', [])

            # Si no hay eventos que choquen, este profesional sirve
            if not events:
                return True, prof.name

        except Exception:
            continue

    return False, None


def search_specific_time_smart(service, professionals, date_obj, time_str, duration):
    """
    Estrategia: Exacto -> Cercano (+/-) -> Mismo horario otros días.
    """
    target_time = datetime.datetime.strptime(time_str, "%H:%M").time()
    target_dt = datetime.datetime.combine(date_obj, target_time, tzinfo=TZ_ARG)

    # 1. Intento EXACTO
    is_free, prof_name = check_slot_availability(service, professionals, target_dt, duration)
    if is_free:
        return [f"✅ Exacto: {date_obj.strftime('%d/%m')} a las {time_str} con {prof_name}"]

    alternatives = []

    # 2. Intento CERCANO (mismo día +/- 40 min)
    offsets = [-duration, duration, -duration * 2, duration * 2]
    for minutes in offsets:
        alt_dt = target_dt + datetime.timedelta(minutes=minutes)
        # Verificar que siga dentro de horario laboral razonable (9-20)
        if 9 <= alt_dt.hour < 20:
            is_free, prof_name = check_slot_availability(service, professionals, alt_dt, duration)
            if is_free:
                alternatives.append(f"⏱️ Cercano: {alt_dt.strftime('%H:%M')} ({prof_name})")
                if len(alternatives) >= 2: break  # Suficientes opciones cercanas

    # 3. Intento OTROS DÍAS (mismo horario, próximos 3 días)
    for i in range(1, 4):
        next_date = date_obj + datetime.timedelta(days=i)
        next_dt = datetime.datetime.combine(next_date, target_time, tzinfo=TZ_ARG)
        is_free, prof_name = check_slot_availability(service, professionals, next_dt, duration)
        if is_free:
            alternatives.append(f"📅 Otro día: {next_date.strftime('%d/%m')} a las {time_str} ({prof_name})")
            if len(alternatives) >= 3: break

    if alternatives:
        return [f"❌ {time_str} ocupado. Opciones:"] + alternatives
    return ["No encontré nada cerca de ese horario."]


def search_range_smart(service, professionals, date_obj, range_tuple, duration):
    """
    Busca en el rango y devuelve 3 opciones distribuidas.
    """
    start_hour, end_hour = range_tuple

    # Generar todos los slots posibles en ese rango
    current_dt = datetime.datetime.combine(date_obj, datetime.time(start_hour, 0), tzinfo=TZ_ARG)
    limit_dt = datetime.datetime.combine(date_obj, datetime.time(end_hour, 0), tzinfo=TZ_ARG)

    available_slots = []

    while current_dt + datetime.timedelta(minutes=duration) <= limit_dt:
        is_free, prof_name = check_slot_availability(service, professionals, current_dt, duration)
        if is_free:
            available_slots.append(f"{current_dt.strftime('%H:%M')} ({prof_name})")

        current_dt += datetime.timedelta(minutes=duration)

    if not available_slots:
        return []

    # ELEGIR 3 OPCIONES REPRESENTATIVAS (Principio, Medio, Final)
    if len(available_slots) <= 3:
        return available_slots

    first = available_slots[0]
    middle = available_slots[len(available_slots) // 2]
    last = available_slots[-1]

    # Asegurar que sean distintos
    selection = {first, middle, last}  # Set elimina duplicados
    return sorted(list(selection))


# --- FUNCIÓN PRINCIPAL EXPORTADA ---

def consultar_disponibilidad(
        db: Session,
        filtros: List[dict],
        tipo_profesional: str,
        nombre_profesional: Optional[str] = None
):
    """
    Procesa filtros inteligentes.
    Regla: Si o Si debe venir 'specific_time' O 'time_range' en el filtro.
    Si 'date' falta, busca el próximo día disponible.
    """
    print(f"🧠 Motor v2: Buscando {tipo_profesional}...")

    # Buscar Profesionales
    profesionales = crud.professional.get_by_type_and_name(db=db, type_prof=tipo_profesional, name_filter=nombre_profesional)

    if not profesionales: return "No hay profesionales cargados."

    service = get_calendar_service()
    if not service: return "Error de conexión Calendar."

    duration = DURATION_MAP.get(ProfessionalType(tipo_profesional), 30)
    resultados = []

    for filtro in filtros:
        # Extraer datos
        date_str = filtro.get("date")
        specific_time = filtro.get("specific_time")
        time_range = filtro.get("time_range")  # Tuple (9, 13)

        # Validación de reglas del usuario
        if not specific_time and not time_range:
            return "⚠️ Error: La IA debe solicitar un horario o rango (mañana/tarde) obligatoriamente."

        # Definir fechas a iterar (Si no hay fecha, probamos hoy + 6 días)
        if date_str:
            dates_to_check = [datetime.date.fromisoformat(date_str)]
        else:
            today = datetime.datetime.now(TZ_ARG).date()
            dates_to_check = [today + datetime.timedelta(days=i) for i in range(7)]

        found_for_filter = False

        for check_date in dates_to_check:
            # Caso A: Hora Puntual
            if specific_time:
                opciones = search_specific_time_smart(service, profesionales, check_date, specific_time, duration)
                # Si encontró algo útil (no mensaje de error genérico), guardamos y cortamos
                if "No encontré" not in opciones[0]:
                    resultados.extend(opciones)
                    found_for_filter = True
                    break  # Encontramos el día, dejamos de buscar en la semana

            # Caso B: Rango Horario
            elif time_range:
                slots = search_range_smart(service, profesionales, check_date, time_range, duration)
                if slots:
                    # Formato: "Lunes 14/12: 09:00, 10:20, 12:00"
                    slots_str = ", ".join(slots)
                    resultados.append(f"🗓️ {check_date.strftime('%A %d/%m')}: {slots_str}")
                    found_for_filter = True
                    break  # Encontramos el día, dejamos de buscar

        if not found_for_filter:
            resultados.append(f"❌ No encontré nada para el criterio (Rango/Hora) en los próximos días.")

    return "\n".join(resultados)

def agendar_evento(calendar_id: str, start_time: str, client_name: str, client_email: str = None) -> dict:
    """
    Crea un evento en Google Calendar.
    Args:
        calendar_id: El ID del calendario (el email del profesional o el ID largo).
        start_time: Fecha y hora de inicio en formato ISO (ej: '2025-12-14T16:00:00').
        client_name: Nombre del cliente para el título del evento.
        client_email: Email del cliente para enviarle invitación (opcional).
    """
    service = get_calendar_service()

    # Convertimos el string ISO a objeto datetime para calcular el final
    # Asumimos que la duración del turno es 1 hora (puedes cambiarlo)
    dt_start = datetime.datetime.fromisoformat(start_time)
    dt_end = dt_start + datetime.timedelta(hours=1)

    event_body = {
        'summary': f'Turno Óptica: {client_name}',
        'description': f'Reserva realizada vía Bot de Instagram. Cliente: {client_name}',
        'start': {
            'dateTime': dt_start.isoformat(),
            'timeZone': 'America/Argentina/Cordoba', # Ajusta a tu zona horaria
        },
        'end': {
            'dateTime': dt_end.isoformat(),
            'timeZone': 'America/Argentina/Cordoba',
        },
    }

    try:
        event = service.events().insert(calendarId=calendar_id, body=event_body).execute()
        return {
            "status": "success",
            "message": "Turno agendado correctamente",
            "link": event.get('htmlLink'),
            "id": event.get('id')
        }
    except Exception as e:
        print(f"Error al crear evento: {e}")
        return {"status": "error", "message": str(e)}

def cancelar_evento(calendar_id: str, event_id: str) -> dict:
    """
    Elimina un evento de Google Calendar liberando el horario.
    Args:
        calendar_id: El ID del calendario (email del profesional).
        event_id: El ID del evento que guardamos en la base de datos.
    """
    service = get_calendar_service()

    try:
        # Ejecutamos la orden de eliminación
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()

        return {
            "status": "success",
            "message": "Turno eliminado de Google Calendar correctamente."
        }
    except Exception as e:
        print(f"Error al cancelar evento en Google: {e}")
        # Si el error es 410 (Gone) o 404 (Not Found), asumimos que ya estaba borrado
        if "404" in str(e) or "410" in str(e):
            return {"status": "success", "message": "El evento ya no existía en Google."}

        return {"status": "error", "message": str(e)}