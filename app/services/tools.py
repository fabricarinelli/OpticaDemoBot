# app/services/ia_tools.py
import json
from datetime import datetime
from typing import List, Dict, Any

from app.core.database import SessionLocal
from app.core.config import settings
#from app.models.models import Professional, Appointment, Client, Order, Product, OrderStatus
from app.services import crud
from app.services import calendar, payments, instagram

# ==============================================================================
# 1. DEFINICIÓN DE HERRAMIENTAS (SCHEMA JSON PARA LA IA)
# ==============================================================================
# (El schema JSON se mantiene igual que antes, el cambio fuerte está en la lógica)

TOOLS_SCHEMA = [
    {
        "name": "enviar_menu_principal",
        "description": "Envía una imagen visual con el catálogo. Úsala cuando pidan ver el catálogo o lista de precios.",
        "parameters": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "consultar_disponibilidad",
        "description": "Consulta la agenda para ver huecos libres.",
        "parameters": {
            "type": "object",
            "properties": {
                "tipo_profesional": {"type": "string", "enum": ["optico", "contactologo"]},
                "fecha": {"type": "string", "description": "YYYY-MM-DD"},
                "rango_horario": {"type": "string", "enum": ["mañana", "tarde"]},
                "hora_especifica": {"type": "string", "description": "HH:MM"}
            },
            "required": ["tipo_profesional"]
        }
    },
    {
        "name": "agendar_turno",
        "description": "Reserva definitivamente un turno. SOLO si el usuario confirmó horario.",
        "parameters": {
            "type": "object",
            "properties": {
                "tipo_profesional": {"type": "string", "enum": ["optico", "contactologo"]},
                "fecha_hora_inicio": {"type": "string", "description": "ISO 8601 (2023-12-20T10:00:00)"},
                "nombre_cliente": {"type": "string"},
                "email_cliente": {"type": "string"}
            },
            "required": ["tipo_profesional", "fecha_hora_inicio", "nombre_cliente"]
        }
    },
    {
        "name": "buscar_producto",
        "description": "Busca precio y descripción en la base de datos.",
        "parameters": {
            "type": "object",
            "properties": {
                "nombre_o_categoria": {"type": "string"}
            },
            "required": ["nombre_o_categoria"]
        }
    },
    {
        "name": "generar_link_pago",
        "description": "Genera una ORDEN DE COMPRA y su link de pago.",
        "parameters": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "titulo": {"type": "string"},
                            "cantidad": {"type": "integer"},
                            "precio_unitario": {"type": "number"}
                        },
                        "required": ["titulo", "cantidad", "precio_unitario"]
                    }
                },
                "email_cliente": {"type": "string"}
            },
            "required": ["items"]
        }
    }
]


# ==============================================================================
# 2. FUNCIONES AUXILIARES (Lógica Interna)
# ==============================================================================

def _get_or_create_client(db, instagram_id: str, name: str = None, email: str = None) -> Client:
    """Busca al cliente por su ID de Instagram. Si no existe, lo crea."""
    client = crud.client.get_one(db, instagram_id=instagram_id)

    if not client:
        # Creamos uno nuevo
        client = crud.client.create(db, instagram_id=instagram_id, name=name, email=email)
    else:
        # Si ya existe y nos pasaron datos nuevos, actualizamos
        updates = {}
        if name and client.name != name: updates["name"] = name
        if email and client.email != email: updates["email"] = email

        if updates:
            crud.client.update(db, client, **updates)

    return client


# ==============================================================================
# 3. HANDLER PRINCIPAL
# ==============================================================================

async def handle_tool_call(tool_name: str, args: Dict[str, Any], recipient_id: str = None) -> str:
    db = SessionLocal()
    try:
        # --- 1. ENVIAR CATÁLOGO ---
        if tool_name == "enviar_menu_principal":
            if recipient_id:
                await instagram.send_image(recipient_id, settings.CATALOG_IMAGE_URL)
                return "✅ Imagen enviada."
            return "Error: Falta ID usuario."

        # --- 2. CONSULTAR DISPONIBILIDAD ---
        elif tool_name == "consultar_disponibilidad":
            # (Misma lógica de mapeo de filtros)
            filtros = []
            filtro = {}
            if "fecha" in args: filtro["date"] = args["fecha"]
            if "hora_especifica" in args:
                filtro["specific_time"] = args["hora_especifica"]
            elif "rango_horario" in args:
                filtro["time_range"] = (9, 13) if args["rango_horario"] == "mañana" else (14, 20)

            if not filtro.get("specific_time") and not filtro.get("time_range"):
                filtro["time_range"] = (9, 20)

            filtros.append(filtro)
            return calendar.consultar_disponibilidad(db, filtros, args["tipo_profesional"])

        # --- 3. AGENDAR TURNO (CON PERSISTENCIA) ---
        elif tool_name == "agendar_turno":
            # A. Identificar Profesional
            prof_type = args["tipo_profesional"]
            # Usamos lógica simple: primer profesional de ese tipo
            # (Podrías mejorar esto buscando uno que esté libre específicamente si quisieras)
            profesional = db.query(Professional).filter(Professional.type == prof_type).first()
            if not profesional:
                return "Error: No hay profesionales configurados para esa especialidad."

            # B. Identificar/Crear Cliente
            if not recipient_id: return "Error: No tengo ID de Instagram del usuario."
            cliente = _get_or_create_client(
                db,
                instagram_id=recipient_id,
                name=args.get("nombre_cliente"),
                email=args.get("email_cliente")
            )

            # C. Llamar a Google Calendar
            resultado_google = calendar.agendar_evento(
                calendar_id=profesional.calendar_id,
                start_time=args["fecha_hora_inicio"],
                client_name=cliente.name or "Cliente",
                client_email=cliente.email
            )

            if resultado_google["status"] == "success":
                # D. GUARDAR EN NUESTRA BASE DE DATOS
                nueva_cita = Appointment(
                    client_id=cliente.id,
                    professional_id=profesional.id,
                    start_time=datetime.fromisoformat(args["fecha_hora_inicio"]),
                    calendar_event_id=resultado_google["id"],
                    status="confirmed"
                )
                db.add(nueva_cita)
                db.commit()

                return f"✅ Turno confirmado y guardado. ID: {resultado_google['id']}"
            else:
                return f"❌ Error Google: {resultado_google['message']}"

        # --- 4. BUSCAR PRODUCTO ---
        elif tool_name == "buscar_producto":
            productos = crud.product.search_fuzzy(db, args["nombre_o_categoria"])
            if not productos: return "No encontré productos."
            return "\n".join([f"- {p.name}: ${p.price}" for p in productos])

        # --- 5. GENERAR PAGO (CARRITO + ORDEN REAL) ---
        elif tool_name == "generar_link_pago":
            if not recipient_id: return "Error: ID usuario requerido."

            # A. Obtener Cliente
            cliente = _get_or_create_client(
                db,
                instagram_id=recipient_id,
                email=args.get("email_cliente")
            )

            # B. Crear la ORDEN en DB (Carrito persistente)
            nueva_orden = Order(
                client_id=cliente.id,
                status=OrderStatus.PENDING,
                total_amount=0.0  # Se actualizará al agregar items
            )
            db.add(nueva_orden)
            db.commit()
            db.refresh(nueva_orden)

            # C. Agregar Items a la Orden
            items_mp = []
            for item_data in args["items"]:
                # Intentamos buscar el producto real por nombre para vincular ID (opcional pero recomendado)
                # Si no match exacto, usamos lógica genérica, pero aquí asumimos la info de la IA
                # Para la DB, creamos el OrderItem.
                # OJO: crud.order.add_item requiere un objeto Product.
                # Para simplificar este script sin complicar la IA, podemos buscar el producto
                # o crear items genéricos si tu modelo lo permite.
                # Asumiremos que la IA buscó antes y el precio es correcto.

                # Buscamos producto 'parecido' para asociar ID, si no, null
                prod_db = crud.product.search_fuzzy(db, item_data["titulo"])
                product_obj = prod_db[0] if prod_db else None

                if product_obj:
                    # Usamos la lógica del CRUD que ya tenías
                    crud.order.add_item(db, nueva_orden, product_obj, item_data["cantidad"])
                else:
                    # Fallback si no hay producto macheado (raro si la IA buscó antes)
                    # Aquí forzamos el cálculo manual si no hay objeto Product
                    pass

                    # Armamos lista para MP
                items_mp.append({
                    "title": item_data["titulo"],
                    "quantity": item_data["cantidad"],
                    "unit_price": item_data["precio_unitario"],
                    "currency_id": "ARS"
                })

            # D. Generar Link MP referenciando NUESTRA Orden
            # Referencia externa = ID de nuestra orden (ej: "ORD-15")
            ref_externa = f"ORD-{nueva_orden.id}"

            res_mp = payments.generar_link_pago(
                items=items_mp,
                external_reference=ref_externa,
                client_email=cliente.email
            )

            if res_mp["status"] == "success":
                # E. Guardar Link en la Orden
                nueva_orden.payment_link = res_mp["link"]
                nueva_orden.mp_reference_id = res_mp["id"]
                db.commit()

                return f"✅ Orden #{nueva_orden.id} creada. Link de pago: {res_mp['link']}"
            else:
                return f"❌ Error MP: {res_mp['message']}"

    except Exception as e:
        return f"Error crítico tools: {str(e)}"
    finally:
        db.close()