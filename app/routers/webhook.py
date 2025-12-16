from fastapi import APIRouter, Request, HTTPException, Query, BackgroundTasks
from app.core.config import settings
from app.services import instagram, gemini, crud
from app.core.database import SessionLocal
from app.services.tools import TOOLS_SCHEMA

router = APIRouter()

# --- CONFIGURACIÓN DE PERSONALIDAD (BARBERÍA) ---
SYSTEM_PROMPT_BARBERIA = """
Sos el asistente virtual de "Barbería Demo". Tu objetivo es gestionar la agenda de turnos de manera eficiente y amigable.

### PERSONALIDAD:
- Hablá en español argentino, tono relajado, moderno y urbano, pero respetuoso y amigable "De una bro" "Dale hermanito" "Mas vale"
- Sos un empleado del lugar, o el barbero, fingí no ser un bot si es posible pero si te preguntan directamente confesa.

### REGLAS DE NEGOCIO (MEMORIA):
1. **Datos del Cliente**: Para agendar, SIEMPRE necesitás:
   - Nombre
   - Teléfono
   (Si el usuario ya te los dijo antes en la charla, usalos. Si no, pedilos).

2. **Turnos**:
   - Primero usá `consultar_disponibilidad` para ver qué hay libre. NUNCA inventes horarios.
   - Solo cuando el usuario confirme un horario específico y tengas sus datos, ejecutá `agendar_turno`.
   - Si quiere cancelar, pedile confirmación y usá `cancelar_turno`.
   - Si quiere cambiar, usá `mover_turno`.

3. **Manejo de Errores**:
   - Si una tool falla (ej: horario ocupado), decíselo al usuario y ofrecé buscar otro horario.
   - Si te faltan datos para una tool, pedilos amablemente.
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

        if message_data.get("is_echo"):
            return

        if 'text' not in message_data:
            return

        user_text = message_data['text']
        print(f"📩 Barbería User {sender_id}: {user_text}")
        client = crud.cliente_barberia.get_one(db, ig_id=sender_id)
        if not client:
            print(f"👤 Nuevo cliente detectado: {sender_id}. Creando registro...")
            client = crud.cliente_barberia.create(db, ig_id=sender_id)
        crud.mensaje_barberia.create(db, cliente_id=client.id, role="user", content=user_text)
        history_for_ai = crud.get_chat_history(db, crud.mensaje_barberia.model, client.id)
        ai_response_text = await gemini.chat_with_gemini(
            user_message=user_text,
            recipient_id=sender_id,
            db_history=history_for_ai,
            tools_schema=TOOLS_SCHEMA,
            system_instruction=SYSTEM_PROMPT_BARBERIA
        )
        if ai_response_text:
            await instagram.send_text(sender_id, ai_response_text)
            crud.mensaje_barberia.create(db, cliente_id=client.id, role="model", content=ai_response_text)

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