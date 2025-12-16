# app/routers/webhook.py
from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Request, HTTPException, Query, BackgroundTasks
from app.core.config import settings
from app.services import instagram, gemini, crud
from app.core.database import SessionLocal
from app.services.tools import TOOLS_SCHEMA

router = APIRouter()

# Zona horaria Argentina
TZ_ARG = ZoneInfo("America/Argentina/Cordoba")

# Prompt Base
SYSTEM_PROMPT_BARBERIA = """
Sos el asistente virtual de "Barbería Demo". Tu objetivo es gestionar la agenda de turnos de manera eficiente y amigable.

###BARBERIA:
Queda en la ciudad de cordoba, argentina, barrio san martin (vos asumí que todos lo que te hablan saben eso). La direccion es Castro Barros 1234. El corte sale 12000. El horario de atencion es de martes a domingos de 9 a 20hs
### PERSONALIDAD:
- Hablá en español argentino, tono relajado, modernno, urbano, respetuoso y amigable ("De una bro", "Dale hermanito", "Nos estamos viendo").
- Sos un empleado del lugar o el barbero. Fingí no ser un bot si es posible, pero si te preguntan directamente, confesá.
- Si no sabes algo, deci que sos un bot y que no tenes esa informacion. No inventes.

### REGLAS DE NEGOCIO (MEMORIA):
1. **Datos del Cliente**: Para agendar, SIEMPRE necesitás tener registrados Nombre y Teléfono.
   - Si no los tenés en tu contexto "DATOS DEL CLIENTE ACTUAL", pedilos y usá la tool `registrar_cliente` para guardarlos antes de agendar.

2. **Turnos**:
   - Primero usá `consultar_disponibilidad`.
   - Solo cuando tengas fecha/hora confirmada Y los datos del cliente, ejecutá `agendar_turno`.
   - Si quiere cancelar, pedile confirmación y usá `cancelar_turno`.
   - Si quiere cambiar, usá `mover_turno`.

3. **Manejo de Errores**:
   - Si una tool falla (ej: horario ocupado), decíselo al usuario y ofrecé opciones.
"""


@router.get("/webhook")
async def verify_webhook(
        mode: str = Query(alias="hub.mode"),
        token: str = Query(alias="hub.verify_token"),
        challenge: str = Query(alias="hub.challenge")
):
    if mode == "subscribe" and token == settings.INSTAGRAM_VERIFY_TOKEN:
        return int(challenge)
    raise HTTPException(status_code=403, detail="Token incorrecto")


async def process_incoming_message(payload: dict):
    db = SessionLocal()
    try:
        try:
            entry = payload['entry'][0]
            messaging = entry['messaging'][0]
            sender_id = messaging['sender']['id']
            message_data = messaging.get('message', {})
        except (IndexError, KeyError):
            return

        if message_data.get("is_echo") or 'text' not in message_data:
            return

        user_text = message_data['text']
        print(f"📩 Barbería User {sender_id}: {user_text}")

        # 1. Obtener / Crear Cliente
        client = crud.cliente_barberia.get_one(db, ig_id=sender_id)
        if not client:
            print(f"👤 Nuevo cliente detectado: {sender_id}. Creando registro...")
            client = crud.cliente_barberia.create(db, ig_id=sender_id)

        # 2. Guardar Mensaje Usuario (Con hora Argentina)
        now_arg = datetime.now(TZ_ARG)
        # Nota: Si tu DB es SQLite, se guardará como string/naive, lo cual está bien.
        # Si usas Postgres, asegúrate que la columna soporte timezone o pasar naive.
        # Para compatibilidad general aquí pasamos con TZ info.
        crud.mensaje_barberia.create(
            db,
            cliente_id=client.id,
            role="user",
            content=user_text,
            timestamp=now_arg
        )

        # 3. Preparar Contexto con Datos del Usuario
        datos_usuario = "No registrados aún."
        if client.nombre or client.telefono:
            datos_usuario = f"Nombre: {client.nombre or 'Falta'}\nTeléfono: {client.telefono or 'Falta'}"

        full_system_prompt = f"{SYSTEM_PROMPT_BARBERIA}\n\n### DATOS DEL CLIENTE ACTUAL (ID: {sender_id}):\n{datos_usuario}"

        history_for_ai = crud.get_chat_history(db, crud.mensaje_barberia.model, client.id)

        # 4. Llamar a Gemini
        ai_response_text = await gemini.chat_with_gemini(
            user_message=user_text,
            recipient_id=sender_id,
            db_history=history_for_ai,
            tools_schema=TOOLS_SCHEMA,
            system_instruction=full_system_prompt
        )

        # 5. Responder y Guardar (Con hora Argentina)
        if ai_response_text:
            await instagram.send_text(sender_id, ai_response_text)

            now_arg_response = datetime.now(TZ_ARG)
            crud.mensaje_barberia.create(
                db,
                cliente_id=client.id,
                role="model",
                content=ai_response_text,
                timestamp=now_arg_response
            )

    except Exception as e:
        print(f"❌ Error procesando webhook barbería: {e}")
    finally:
        db.close()


@router.post("/webhook")
async def receive_instagram_message(request: Request, background_tasks: BackgroundTasks):
    try:
        payload = await request.json()
        background_tasks.add_task(process_incoming_message, payload)
        return {"status": "received"}
    except Exception as e:
        return {"status": "error"}