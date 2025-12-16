import datetime
import os.path
from typing import List, Optional
from zoneinfo import ZoneInfo

from google.oauth2 import service_account
from googleapiclient.discovery import build
from app.core.config import settings

# --- CONFIGURACIÓN ---
SCOPES = ['https://www.googleapis.com/auth/calendar']
TZ_ARG = ZoneInfo("America/Argentina/Cordoba")
WORK_HOURS = {"start": 9, "end": 20}


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


# --- LÓGICA DE DISPONIBILIDAD (BARBERÍA) ---

def check_slot_availability(service, calendar_id, slot_start):
    """
    Verifica si el calendario específico está libre en ese horario.
    Retorna True si está libre.
    """
    slot_end = slot_start + datetime.timedelta(minutes=60)

    time_min = slot_start.isoformat()
    time_end = slot_end.isoformat()

    try:
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_end,
            singleEvents=True
        ).execute()
        events = events_result.get('items', [])

        # Si no hay eventos superpuestos, está libre
        if not events:
            return True

    except Exception as e:
        print(f"Error consultando slot: {e}")
        return False

    return False


def search_availability(service, calendar_id, date_obj, specific_time=None, time_range=None):
    """
    Busca disponibilidad basándose en hora exacta o rango.
    """
    resultados = []

    # Generamos los slots a revisar
    slots_to_check = []

    if specific_time:
        # Caso 1: Hora exacta
        target_time = datetime.datetime.strptime(specific_time, "%H:%M").time()
        start_dt = datetime.datetime.combine(date_obj, target_time, tzinfo=TZ_ARG)
        slots_to_check.append(start_dt)

        # Opcional: Agregar lógica "fuzzy" (buscar +/- 1 hora) si la exacta falla
        # tal como tenías en la versión anterior si deseas mantener esa inteligencia.

    elif time_range:
        # Caso 2: Rango (ej: mañana 9-13)
        start_hour, end_hour = time_range
        current_dt = datetime.datetime.combine(date_obj, datetime.time(start_hour, 0), tzinfo=TZ_ARG)
        limit_dt = datetime.datetime.combine(date_obj, datetime.time(end_hour, 0), tzinfo=TZ_ARG)

        while current_dt + datetime.timedelta(minutes=60) <= limit_dt:
            slots_to_check.append(current_dt)
            current_dt += datetime.timedelta(minutes=60)  # Saltos de 60 min

    # Verificamos disponibilidad
    disponibles = []
    for slot in slots_to_check:
        if check_slot_availability(service, calendar_id, slot):
            disponibles.append(slot.strftime('%H:%M'))
            # Si es rango, limitamos para no saturar
            if time_range and len(disponibles) >= 4:
                break

    return disponibles

def consultar_disponibilidad(
        filtros: List[dict]
) -> str:
    """
    Consulta disponibilidad en el calendario de la Barbería.
    Ya no requiere db ni tipo_profesional.
    """
    calendar_id = settings.BARBER_CALENDAR_ID

    service = get_calendar_service()
    if not service: return "Error de conexión con Google Calendar."

    mensajes_respuesta = []

    for filtro in filtros:
        date_str = filtro.get("date")
        specific_time = filtro.get("specific_time")
        time_range = filtro.get("time_range")

        # Determinar fecha(s) a buscar
        dates_to_check = []
        if date_str:
            dates_to_check.append(datetime.date.fromisoformat(date_str))
        else:
            # Si no especifica fecha, buscar en los próximos 3 días
            today = datetime.datetime.now(TZ_ARG).date()
            dates_to_check = [today + datetime.timedelta(days=i) for i in range(3)]

        for check_date in dates_to_check:
            slots = search_availability(service, calendar_id, check_date, specific_time, time_range)

            if slots:
                slots_str = ", ".join(slots)
                mensajes_respuesta.append(f"🗓️ {check_date.strftime('%A %d/%m')}: {slots_str}")
            elif specific_time:
                mensajes_respuesta.append(f"❌ El {check_date.strftime('%d/%m')} a las {specific_time} está ocupado.")

    if not mensajes_respuesta:
        return "No encontré horarios disponibles con esos criterios. ¿Podrías probar otro día u horario?"

    return "\n".join(mensajes_respuesta)


def agendar_evento(start_time: str, client_name: str, client_phone: str, client_email: str = None) -> dict:
    """
    Reserva el turno cumpliendo RF-1.4 (Título con nombre y teléfono).
    """
    calendar_id = settings.BARBER_CALENDAR_ID
    service = get_calendar_service()

    dt_start = datetime.datetime.fromisoformat(start_time)
    dt_end = dt_start + datetime.timedelta(minutes=60)

    # RF-1.4: Título formateado
    summary = f"Turno: {client_name} - {client_phone}"

    description = f"Reserva Barbería Demo.\nCliente: {client_name}\nTel: {client_phone}"
    if client_email:
        description += f"\nEmail: {client_email}"

    event_body = {
        'summary': summary,
        'description': description,
        'start': {
            'dateTime': dt_start.isoformat(),
            'timeZone': 'America/Argentina/Cordoba',
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


def cancelar_evento(event_id: str) -> dict:
    """
    Elimina el evento del calendario de la Barbería.
    """
    calendar_id = settings.BARBER_CALENDAR_ID
    service = get_calendar_service()

    try:
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        return {"status": "success", "message": "Turno cancelado correctamente."}
    except Exception as e:
        if "404" in str(e) or "410" in str(e):
            return {"status": "success", "message": "El turno ya no existía."}
        return {"status": "error", "message": str(e)}