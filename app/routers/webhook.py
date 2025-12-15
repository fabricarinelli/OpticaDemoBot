# app/routers/webhook.py
from fastapi import APIRouter, Request, HTTPException, Query, BackgroundTasks
from sqlalchemy import desc
from app.core.config import settings
from app.services import instagram, gemini
from app.core.database import SessionLocal
from app.models.models import Client, Message
from app.services import crud  # Asumiendo que tienes un crud genérico o usas la session directo

router = APIRouter()


# --- VERIFICACIÓN (Igual que siempre) ---
@router.get("/webhook")
async def verify_webhook(
        mode: str = Query(alias="hub.mode"),
        token: str = Query(alias="hub.verify_token"),
        challenge: str = Query(alias="hub.challenge")
):
    if mode == "subscribe" and token == settings.INSTAGRAM_VERIFY_TOKEN:
        return int(challenge)
    raise HTTPException(status_code=403, detail="Token incorrecto")


# --- PROCESAMIENTO INTELIGENTE ---
async def process_incoming_message(payload: dict):
    db = SessionLocal()
    try:
        # 1. Extraer datos
        entry = payload['entry'][0]
        messaging = entry['messaging'][0]
        sender_id = messaging['sender']['id']

        # Ignorar si no es texto
        if 'message' not in messaging or 'text' not in messaging['message']:
            return
        if message.get("is_echo"):
            print("🔄 Ignorando mensaje enviado por el bot (Echo)")
            continue
        user_text = messaging['message']['text']
        print(f"📩 User {sender_id}: {user_text}")

        # 2. IDENTIFICAR O CREAR CLIENTE (Vital para asociar memoria)
        client = db.query(Client).filter(Client.instagram_id == sender_id).first()
        if not client:
            client = Client(instagram_id=sender_id)
            db.add(client)
            db.commit()
            db.refresh(client)

        # 3. GUARDAR MENSAJE DEL USUARIO EN DB (¡Esto faltaba!)
        msg_user = Message(client_id=client.id, role="user", content=user_text)
        db.add(msg_user)
        db.commit()

        # 4. RECUPERAR HISTORIAL (Últimos 10 mensajes)
        # Ordenamos por ID descendente, tomamos 10 y luego los invertimos para que estén en orden cronológico
        last_messages = db.query(Message) \
            .filter(Message.client_id == client.id) \
            .order_by(desc(Message.id)) \
            .limit(10) \
            .all()

        # Invertimos la lista para que Gemini la lea en orden (antiguo -> nuevo)
        history_for_ai = last_messages[::-1]

        # 5. CEREBRO: Llamar a Gemini con el historial real
        ai_response_text = await gemini.chat_with_gemini(
            user_message=user_text,
            recipient_id=sender_id,
            db_history=history_for_ai
        )

        # 6. RESPONDER Y GUARDAR
        if ai_response_text:
            # Enviar a Instagram
            await instagram.send_text(sender_id, ai_response_text)

            # GUARDAR RESPUESTA DE LA IA EN DB (¡Para que se acuerde después!)
            msg_ai = Message(client_id=client.id, role="model", content=ai_response_text)
            db.add(msg_ai)
            db.commit()

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