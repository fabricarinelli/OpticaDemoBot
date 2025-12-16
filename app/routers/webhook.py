from fastapi import APIRouter, Request, HTTPException, Query, BackgroundTasks
from app.core.config import settings
from app.services import instagram, gemini, crud  # Importamos crud
from app.core.database import SessionLocal

# Ya no necesitamos importar los Models ni desc aquí, el crud se encarga

router = APIRouter()


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
        # 1. Extraer datos con seguridad
        try:
            entry = payload['entry'][0]
            messaging = entry['messaging'][0]
            sender_id = messaging['sender']['id']
            message_data = messaging.get('message', {})  # Extraemos el objeto message aquí
        except (IndexError, KeyError):
            return

        # --- CORRECCIÓN DEL ERROR ---
        # 1. Usamos message_data en vez de 'message' (variable que no existía)
        # 2. Usamos return en vez de continue (porque no hay bucle)
        if message_data.get("is_echo"):
            print("🔄 Ignorando mensaje enviado por el bot (Echo)")
            return

        if 'text' not in message_data:
            return

        user_text = message_data['text']
        print(f"📩 User {sender_id}: {user_text}")

        # 2. IDENTIFICAR CLIENTE (Usando CRUD)
        # get_one devuelve None si no existe, simplificando la lógica
        current_client = crud.client.get_one(db, instagram_id=sender_id)

        if not current_client:
            # create ya hace el add, commit y refresh por vos
            current_client = crud.client.create(db, instagram_id=sender_id)

        # 3. GUARDAR MENSAJE USER (Usando CRUD)
        crud.message.create(db, client_id=current_client.id, role="user", content=user_text)

        # 4. RECUPERAR HISTORIAL (Usando el método nuevo en CRUD)
        history_for_ai = crud.message.get_chat_history(db, client_id=current_client.id)

        # 5. CEREBRO
        ai_response_text = await gemini.chat_with_gemini(
            user_message=user_text,
            recipient_id=sender_id,
            db_history=history_for_ai
        )

        # 6. RESPONDER Y GUARDAR
        if ai_response_text:
            await instagram.send_text(sender_id, ai_response_text)

            # Guardar respuesta IA con CRUD
            crud.message.create(db, client_id=current_client.id, role="model", content=ai_response_text)

    except Exception as e:
        print(f"❌ Error procesando webhook: {e}")
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