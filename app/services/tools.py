# app/services/tools.py
from datetime import datetime
from typing import List, Dict, Any

from app.core.database import SessionLocal
from app.services import crud, calendar, instagram
from app.models.models import TurnoBarberia

# ==============================================================================
# 1. DEFINICIÓN DE HERRAMIENTAS (SCHEMA JSON PARA LA IA)
# ==============================================================================

TOOLS_SCHEMA = [
    {
        "name": "consultar_disponibilidad",
        "description": "Consulta la agenda de la barbería para ver horarios disponibles.",
        "parameters": {
            "type": "object",
            "properties": {
                "fecha": {"type": "string",
                          "description": "Fecha en formato YYYY-MM-DD. Si no se especifica, se asume hoy/mañana."},
                "rango_horario": {"type": "string", "enum": ["mañana", "tarde"],
                                  "description": "Preferencia de turno."},
                "hora_especifica": {"type": "string", "description": "Hora exacta en formato HH:MM"}
            },
            "required": []
        }
    },
    {
        "name": "agendar_turno",
        "description": "Reserva un turno confirmado. Requiere nombre y teléfono.",
        "parameters": {
            "type": "object",
            "properties": {
                "fecha_hora_inicio": {"type": "string",
                                      "description": "Fecha y hora ISO 8601 (ej: 2024-12-20T10:00:00)."},
                "nombre_cliente": {"type": "string", "description": "Nombre completo del cliente."},
                "telefono_cliente": {"type": "string", "description": "Número de teléfono para contacto."}
            },
            "required": ["fecha_hora_inicio", "nombre_cliente", "telefono_cliente"]
        }
    },
    {
        "name": "cancelar_turno",
        "description": "Cancela un turno existente.",
        "parameters": {
            "type": "object",
            "properties": {
                "telefono_cliente": {"type": "string",
                                     "description": "Para verificar la identidad del turno a cancelar."}
            },
            "required": []
        }
    },
    {
        "name": "mover_turno",
        "description": "Reprograma un turno: cancela el anterior y crea uno nuevo.",
        "parameters": {
            "type": "object",
            "properties": {
                "telefono_cliente": {"type": "string"},
                "fecha_hora_nueva": {"type": "string", "description": "Nueva fecha y hora ISO 8601."}
            },
            "required": ["fecha_hora_nueva"]
        }
    }
]


# ==============================================================================
# 2. HANDLER PRINCIPAL
# ==============================================================================

async def handle_tool_call(tool_name: str, args: Dict[str, Any], recipient_id: str = None) -> str:
    """
    Controlador central que recibe la orden de Gemini y ejecuta la lógica de negocio.
    """
    db = SessionLocal()
    try:
        # ----------------------------------------------------------------------
        # TOOL: CONSULTAR DISPONIBILIDAD
        # ----------------------------------------------------------------------
        if tool_name == "consultar_disponibilidad":
            # Mapeamos los argumentos simples de la IA a la estructura de filtros del calendar service
            filtros = []
            filtro = {}

            if "fecha" in args:
                filtro["date"] = args["fecha"]

            if "hora_especifica" in args:
                filtro["specific_time"] = args["hora_especifica"]
            elif "rango_horario" in args:
                # Definimos rangos fijos para simplificar
                filtro["time_range"] = (9, 13) if args["rango_horario"] == "mañana" else (14, 20)
            else:
                # Si no especifica nada, buscamos en todo el día laboral
                filtro["time_range"] = (9, 20)

            filtros.append(filtro)

            # Llamamos al servicio de calendario (ya refactorizado)
            return calendar.consultar_disponibilidad(filtros)

        # ----------------------------------------------------------------------
        # TOOL: AGENDAR TURNO
        # ----------------------------------------------------------------------
        elif tool_name == "agendar_turno":
            if not recipient_id:
                return "Error: No se pudo identificar al usuario de Instagram."

            # 1. Gestión de Cliente en DB (Barbería)
            # Buscamos o creamos el cliente
            cliente = crud.cliente_barberia.get_one(db, ig_id=recipient_id)
            if not cliente:
                cliente = crud.cliente_barberia.create(
                    db,
                    ig_id=recipient_id,
                    nombre=args.get("nombre_cliente"),
                    telefono=args.get("telefono_cliente")
                )
            else:
                # Actualizamos datos si vienen nuevos
                updates = {}
                if args.get("nombre_cliente"): updates["nombre"] = args["nombre_cliente"]
                if args.get("telefono_cliente"): updates["telefono"] = args["telefono_cliente"]
                if updates:
                    crud.cliente_barberia.update(db, cliente, **updates)

            # 2. Llamada a Google Calendar API
            res_google = calendar.agendar_evento(
                start_time=args["fecha_hora_inicio"],
                client_name=cliente.nombre,
                client_phone=cliente.telefono,
                client_email=None  # Opcional
            )

            if res_google["status"] == "success":
                # 3. Guardar Turno en DB
                crud.turno_barberia.create(
                    db,
                    cliente_id=cliente.id,
                    fecha_hora=datetime.fromisoformat(args["fecha_hora_inicio"]),
                    google_event_id=res_google["id"],
                    estado="activo",
                    nota="Reserva vía Bot"
                )
                return f"✅ ¡Listo {cliente.nombre}! Turno agendado con éxito."
            else:
                return f"❌ Hubo un error al intentar reservar en el calendario: {res_google['message']}"

        # ----------------------------------------------------------------------
        # TOOL: CANCELAR TURNO
        # ----------------------------------------------------------------------
        elif tool_name == "cancelar_turno":
            if not recipient_id: return "Error ID usuario."

            # 1. Buscar cliente
            cliente = crud.cliente_barberia.get_one(db, ig_id=recipient_id)
            if not cliente:
                return "No tienes turnos registrados con nosotros."

            # 2. Buscar turno ACTIVO futuro
            # (Simplificación: traemos el último activo. En producción idealmente se lista)
            turnos = crud.turno_barberia.get_multi(
                db,
                cliente_id=cliente.id,
                estado="activo"
            )

            # Filtramos en memoria solo los futuros para asegurar
            turnos_futuros = [t for t in turnos if t.fecha_hora > datetime.now()]

            if not turnos_futuros:
                return "No encontré ningún turno futuro activo para cancelar."

            turno_a_cancelar = turnos_futuros[0]  # Tomamos el más próximo

            # 3. Borrar de Google Calendar
            res_google = calendar.cancelar_evento(turno_a_cancelar.google_event_id)

            # 4. Actualizar DB
            if res_google["status"] == "success":
                crud.turno_barberia.update(db, turno_a_cancelar, estado="cancelado")
                return f"✅ Turno del {turno_a_cancelar.fecha_hora.strftime('%d/%m %H:%M')} cancelado correctamente."
            else:
                return "Hubo un error técnico al intentar cancelar el evento en Google."

        # ----------------------------------------------------------------------
        # TOOL: MOVER TURNO (REPROGRAMAR)
        # ----------------------------------------------------------------------
        elif tool_name == "mover_turno":
            # Estrategia SRS: Cancelar anterior + Crear nuevo

            # A. Ejecutar lógica de cancelación (Reutilizamos lógica interna)
            cliente = crud.cliente_barberia.get_one(db, ig_id=recipient_id)
            if not cliente: return "No tienes turnos para reprogramar."

            turnos = crud.turno_barberia.get_multi(db, cliente_id=cliente.id, estado="activo")
            turnos_futuros = [t for t in turnos if t.fecha_hora > datetime.now()]

            if not turnos_futuros:
                return "No tenés turnos activos para cambiar. ¿Querés agendar uno nuevo?"

            turno_viejo = turnos_futuros[0]

            # B. Intentar agendar el NUEVO primero (para ver si hay lugar)
            #    Si falla el nuevo, no cancelamos el viejo.
            res_google_new = calendar.agendar_evento(
                start_time=args["fecha_hora_nueva"],
                client_name=cliente.nombre,
                client_phone=cliente.telefono or args.get("telefono_cliente")
            )

            if res_google_new["status"] != "success":
                return f"❌ No pude reprogramar: El horario nuevo no está disponible o hubo un error ({res_google_new['message']}). Tu turno anterior sigue vigente."

            # C. Si el nuevo se creó, procedemos a borrar el viejo
            calendar.cancelar_evento(turno_viejo.google_event_id)

            # D. Actualizar DB
            # 1. Cancelar viejo
            crud.turno_barberia.update(db, turno_viejo, estado="reprogramado_old")

            # 2. Crear nuevo
            crud.turno_barberia.create(
                db,
                cliente_id=cliente.id,
                fecha_hora=datetime.fromisoformat(args["fecha_hora_nueva"]),
                google_event_id=res_google_new["id"],
                estado="activo",
                nota="Reprogramado"
            )

            return "✅ Turno cambiado exitosamente."

        else:
            return f"Herramienta no reconocida: {tool_name}"

    except Exception as e:
        print(f"Error crítico en tools: {e}")
        return "Ocurrió un error interno procesando la solicitud."
    finally:
        db.close()