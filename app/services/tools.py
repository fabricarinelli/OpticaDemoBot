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
        "name": "registrar_cliente",
        "description": "Guarda los datos personales del cliente (nombre y teléfono) en la base de datos.",
        "parameters": {
            "type": "object",
            "properties": {
                "nombre": {"type": "string", "description": "Nombre del cliente"},
                "telefono": {"type": "string", "description": "Teléfono del cliente"}
            },
            "required": ["nombre", "telefono"]
        }
    },
    {
        "name": "agendar_turno",
        "description": "Reserva un turno confirmado. Usar SOLO si ya tenemos los datos del cliente registrados o si se pasan aquí.",
        "parameters": {
            "type": "object",
            "properties": {
                "fecha_hora_inicio": {"type": "string",
                                      "description": "Fecha y hora ISO 8601 (ej: 2024-12-20T10:00:00)."},
                "nombre_cliente": {"type": "string",
                                   "description": "Nombre completo del cliente (opcional si ya está registrado)."},
                "telefono_cliente": {"type": "string",
                                     "description": "Número de teléfono (opcional si ya está registrado)."}
            },
            "required": ["fecha_hora_inicio"]
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
            filtros = []
            filtro = {}

            if "fecha" in args:
                filtro["date"] = args["fecha"]

            if "hora_especifica" in args:
                filtro["specific_time"] = args["hora_especifica"]
            elif "rango_horario" in args:
                filtro["time_range"] = (9, 13) if args["rango_horario"] == "mañana" else (14, 20)
            else:
                filtro["time_range"] = (9, 20)

            filtros.append(filtro)
            return calendar.consultar_disponibilidad(filtros)

        # ----------------------------------------------------------------------
        # TOOL: REGISTRAR CLIENTE
        # ----------------------------------------------------------------------
        elif tool_name == "registrar_cliente":
            if not recipient_id: return "Error: No ID usuario."

            cliente = crud.cliente_barberia.get_one(db, ig_id=recipient_id)
            if not cliente:
                crud.cliente_barberia.create(
                    db,
                    ig_id=recipient_id,
                    nombre=args.get("nombre"),
                    telefono=args.get("telefono")
                )
            else:
                crud.cliente_barberia.update(
                    db,
                    cliente,
                    nombre=args.get("nombre"),
                    telefono=args.get("telefono")
                )
            return "✅ Datos del cliente actualizados correctamente."

        # ----------------------------------------------------------------------
        # TOOL: AGENDAR TURNO
        # ----------------------------------------------------------------------
        elif tool_name == "agendar_turno":
            if not recipient_id:
                return "Error: No se pudo identificar al usuario de Instagram."

            # 1. Recuperar o actualizar cliente
            cliente = crud.cliente_barberia.get_one(db, ig_id=recipient_id)
            if not cliente:
                # Si no existe, lo creamos con lo que venga (si viene)
                cliente = crud.cliente_barberia.create(
                    db,
                    ig_id=recipient_id,
                    nombre=args.get("nombre_cliente"),
                    telefono=args.get("telefono_cliente")
                )
            else:
                # Si ya existe, actualizamos si mandaron datos nuevos
                updates = {}
                if args.get("nombre_cliente"): updates["nombre"] = args["nombre_cliente"]
                if args.get("telefono_cliente"): updates["telefono"] = args["telefono_cliente"]
                if updates:
                    crud.cliente_barberia.update(db, cliente, **updates)

            # Validar que tengamos datos reales antes de ir a Google
            nombre_final = cliente.nombre or "Cliente"
            telefono_final = cliente.telefono or "Sin teléfono"

            # 2. Llamada a Google Calendar API
            res_google = calendar.agendar_evento(
                start_time=args["fecha_hora_inicio"],
                client_name=nombre_final,
                client_phone=telefono_final,
                client_email=None
            )

            if res_google["status"] == "success":
                crud.turno_barberia.create(
                    db,
                    cliente_id=cliente.id,
                    fecha_hora=datetime.fromisoformat(args["fecha_hora_inicio"]),
                    google_event_id=res_google["id"],
                    estado="activo",
                    nota="Reserva vía Bot"
                )
                return f"✅ Turno agendado con éxito para {nombre_final}. El link es {res_google["link"]}"
            else:
                return f"❌ Hubo un error al intentar reservar en el calendario: {res_google['message']}"

        # ----------------------------------------------------------------------
        # TOOL: CANCELAR TURNO
        # ----------------------------------------------------------------------
        elif tool_name == "cancelar_turno":
            if not recipient_id: return "Error ID usuario."

            cliente = crud.cliente_barberia.get_one(db, ig_id=recipient_id)
            if not cliente:
                return "No tienes turnos registrados con nosotros."

            # Buscar turnos activos futuros
            turnos = crud.turno_barberia.get_multi(db, cliente_id=cliente.id, estado="activo")
            turnos_futuros = [t for t in turnos if t.fecha_hora > datetime.now()]

            if not turnos_futuros:
                return "No encontré ningún turno futuro activo para cancelar."

            turno_a_cancelar = turnos_futuros[0]

            res_google = calendar.cancelar_evento(turno_a_cancelar.google_event_id)

            if res_google["status"] == "success":
                crud.turno_barberia.update(db, turno_a_cancelar, estado="cancelado")
                return f"✅ Turno del {turno_a_cancelar.fecha_hora.strftime('%d/%m %H:%M')} cancelado correctamente."
            else:
                return "Hubo un error técnico al intentar cancelar el evento en Google."

        # ----------------------------------------------------------------------
        # TOOL: MOVER TURNO
        # ----------------------------------------------------------------------
        elif tool_name == "mover_turno":
            cliente = crud.cliente_barberia.get_one(db, ig_id=recipient_id)
            if not cliente: return "No tienes turnos para reprogramar."

            turnos = crud.turno_barberia.get_multi(db, cliente_id=cliente.id, estado="activo")
            turnos_futuros = [t for t in turnos if t.fecha_hora > datetime.now()]

            if not turnos_futuros:
                return "No tenés turnos activos para cambiar. ¿Querés agendar uno nuevo?"

            turno_viejo = turnos_futuros[0]

            # Intentar agendar el nuevo
            res_google_new = calendar.agendar_evento(
                start_time=args["fecha_hora_nueva"],
                client_name=cliente.nombre,
                client_phone=cliente.telefono or args.get("telefono_cliente")
            )

            if res_google_new["status"] != "success":
                return f"❌ No pude reprogramar: El horario nuevo no está disponible o hubo un error ({res_google_new['message']})."

            # Si el nuevo funcionó, borramos el viejo
            calendar.cancelar_evento(turno_viejo.google_event_id)

            # Actualizar DB
            crud.turno_barberia.update(db, turno_viejo, estado="reprogramado_old")

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